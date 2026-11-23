import test from "node:test";
import assert from "node:assert/strict";

import { createBrowserApi } from "../shared/browser-api.js";
import { CaptureController } from "../shared/capture-controller.js";
import { createDefaultBrowserCaptureConfig, validateRuntimeConfig } from "../shared/config-validator.js";
import { NativeBridge, computeSha256Hex, decodeImageDataUrl } from "../shared/native-bridge.js";

// PNG 1x1 transparan valid dalam base64
const SAMPLE_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";
const SAMPLE_PNG_DATA_URL = `data:image/png;base64,${SAMPLE_PNG_BASE64}`;

function createEventSource() {
  const listeners = [];
  return {
    addListener(fn) {
      listeners.push(fn);
    },
    emit(...args) {
      for (const fn of [...listeners]) {
        fn(...args);
      }
    },
  };
}

function createMockWebExtensionEnv({ browserName = "chrome", initialUrl = "https://www.konstantaedu.com/tryout", hasAllUrls = false } = {}) {
  const storageData = {};
  const badgeState = { text: "", color: "", title: "" };
  const alarmsCreated = new Map();
  let activeTab = { id: 101, windowId: 1, active: true, url: initialUrl };
  let hostPermission = hasAllUrls;
  let captureCount = 0;
  let captureError = null;
  let currentPort = null;
  const sentHostMessages = [];

  const events = {
    tabsActivated: createEventSource(),
    tabsUpdated: createEventSource(),
    tabsRemoved: createEventSource(),
    windowFocusChanged: createEventSource(),
    alarmFired: createEventSource(),
    permAdded: createEventSource(),
    permRemoved: createEventSource(),
  };

  const makePort = () => {
    const onMessage = createEventSource();
    const onDisconnect = createEventSource();
    const port = {
      onMessage,
      onDisconnect,
      postMessage(msg) {
        sentHostMessages.push(msg);
      },
      disconnect() {
        onDisconnect.emit();
      },
      simulateIncoming(msg) {
        onMessage.emit(msg);
      },
      simulateCrash() {
        onDisconnect.emit();
      },
    };
    currentPort = port;
    return port;
  };

  const rawApi = {
    runtime: {
      id: browserName === "firefox" ? "loveyou-capture@xoose.local" : "abcdefghijklmnopabcdefghijklmnop",
      getManifest: () => ({ version: "1.0.0" }),
      connectNative: () => makePort(),
      sendMessage: async () => ({ ok: true }),
      onMessage: createEventSource(),
      onInstalled: createEventSource(),
      onStartup: createEventSource(),
    },
    tabs: {
      query: async () => (activeTab ? [activeTab] : []),
      get: async (id) => (activeTab && activeTab.id === id ? activeTab : null),
      captureVisibleTab: async (_winId, _opts) => {
        if (captureError) {
          throw new Error(captureError);
        }
        captureCount += 1;
        return SAMPLE_PNG_DATA_URL;
      },
      onActivated: events.tabsActivated,
      onUpdated: events.tabsUpdated,
      onRemoved: events.tabsRemoved,
    },
    windows: {
      WINDOW_ID_NONE: -1,
      get: async () => ({ id: 1, focused: true }),
      getLastFocused: async () => ({ id: 1, focused: true }),
      onFocusChanged: events.windowFocusChanged,
    },
    alarms: {
      create(name, info) {
        alarmsCreated.set(name, info);
      },
      clear: async (name) => alarmsCreated.delete(name),
      get: async (name) => alarmsCreated.get(name) || null,
      onAlarm: events.alarmFired,
    },
    storage: {
      local: {
        get: async (key) => (typeof key === "string" ? { [key]: storageData[key] } : { ...storageData }),
        set: async (items) => {
          Object.assign(storageData, items);
        },
        remove: async (key) => {
          delete storageData[key];
        },
      },
    },
    permissions: {
      contains: async () => hostPermission,
      request: async () => {
        hostPermission = true;
        return true;
      },
      remove: async () => {
        hostPermission = false;
        return true;
      },
      onAdded: events.permAdded,
      onRemoved: events.permRemoved,
    },
    action: {
      setBadgeText: async ({ text }) => {
        badgeState.text = text;
      },
      setBadgeBackgroundColor: async ({ color }) => {
        badgeState.color = color;
      },
      setBadgeTextColor: async () => {},
      setTitle: async ({ title }) => {
        badgeState.title = title;
      },
    },
  };

  const api = createBrowserApi(rawApi, browserName);

  return {
    api,
    events,
    badgeState,
    alarmsCreated,
    sentHostMessages,
    getPort: () => currentPort,
    getCaptureCount: () => captureCount,
    setActiveTab(nextTab) {
      activeTab = nextTab;
    },
    setHostPermission(val) {
      hostPermission = val;
    },
    setCaptureError(err) {
      captureError = err;
    },
  };
}

function makeLiveConfig({
  version = 1,
  activeSource = "browser_domain",
  enabled = true,
  permissionMode = "local_start",
  localSessionRequired = true,
  domain = "konstantaedu.com",
  includeSubdomains = true,
  intervalSeconds = 10,
} = {}) {
  return {
    type: "config_update",
    config_version: version,
    active_source: activeSource,
    browser_capture: {
      enabled,
      capture_mode: "active_tab",
      permission_mode: permissionMode,
      local_session_required: localSessionRequired,
      pause_when_browser_unfocused: true,
      pause_when_tab_inactive: true,
      image_format: "webp",
      fallback_format: "png",
      capture_interval_seconds: intervalSeconds,
      rules: [
        {
          id: "konstanta-domain",
          enabled: true,
          domain,
          include_subdomains: includeSubdomains,
          schemes: ["https"],
          browsers: ["chrome", "edge", "firefox"],
        },
      ],
    },
  };
}

test("Default config selalu enabled=false dan validator menolak config berbahaya/invalid", () => {
  const def = createDefaultBrowserCaptureConfig();
  assert.equal(def.browser_capture.enabled, false);
  assert.equal(def.browser_capture.permission_mode, "local_start");
  assert.equal(def.browser_capture.capture_mode, "active_tab");

  const invalidWildcard = validateRuntimeConfig(makeLiveConfig({ domain: "*.konstantaedu.com" }));
  assert.equal(invalidWildcard.ok, false);

  const invalidMode = validateRuntimeConfig({
    ...makeLiveConfig(),
    browser_capture: { ...makeLiveConfig().browser_capture, capture_mode: "background_tab" },
  });
  assert.equal(invalidMode.ok, false);

  const invalidInterval = validateRuntimeConfig(makeLiveConfig({ intervalSeconds: 0 }));
  assert.equal(invalidInterval.ok, false);

  const dupRules = validateRuntimeConfig({
    ...makeLiveConfig(),
    browser_capture: {
      ...makeLiveConfig().browser_capture,
      rules: [makeLiveConfig().browser_capture.rules[0], makeLiveConfig().browser_capture.rules[0]],
    },
  });
  assert.equal(dupRules.ok, false);
});

test("Active tab capture sukses lintas Chrome, Edge, dan Firefox dengan chunk + SHA-256 valid", async () => {
  for (const browserName of ["chrome", "edge", "firefox"]) {
    const env = createMockWebExtensionEnv({ browserName, initialUrl: "https://www.konstantaedu.com/ujian/123?secret=1" });
    let nowMs = 1_700_000_000_000;
    const bridge = new NativeBridge({ api: env.api });
    const controller = new CaptureController({
      api: env.api,
      bridge,
      nowFn: () => nowMs,
      enableSubMinuteTimer: false,
    });
    await controller.init();

    // Default sebelum config admin masuk: tidak menangkap layar
    const before = await controller.captureIfEligible("immediate");
    assert.equal(before.captured, false);
    assert.equal(env.getCaptureCount(), 0);

    // Terima config live dari Agent
    const applyRes = await controller.applyRuntimeConfig(makeLiveConfig({ version: 2 }));
    assert.equal(applyRes.ok, true);

    // Mode local_start default mewajibkan klik Start lokal pengguna
    const beforeStart = await controller.captureIfEligible("immediate");
    assert.equal(beforeStart.captured, false);
    assert.equal(beforeStart.reason, "local_stopped");

    // Pengguna menekan tombol Mulai di popup -> langsung menangkap 1x
    const snap = await controller.handleLocalControl("start");
    assert.equal(snap.capture_state, "capturing");
    assert.equal(snap.matched_domain, "www.konstantaedu.com");
    assert.equal(env.getCaptureCount(), 1);
    assert.equal(env.badgeState.text, "ON");

    const chunkMsgs = env.sentHostMessages.filter((m) => m.type === "capture_chunk");
    assert.equal(chunkMsgs.length, 1);
    assert.equal(chunkMsgs[0].meta.source, "browser_tab");
    assert.equal(chunkMsgs[0].meta.browser, browserName);
    assert.equal(chunkMsgs[0].meta.origin_domain, "www.konstantaedu.com");
    assert.equal(chunkMsgs[0].meta.rule_id, "konstanta-domain");
    assert.equal(chunkMsgs[0].target_format, "webp");

    const { bytes } = decodeImageDataUrl(SAMPLE_PNG_DATA_URL);
    const expectedSha = await computeSha256Hex(bytes);
    assert.equal(chunkMsgs[0].checksum, expectedSha);

    bridge.disconnect();
  }
});

test("Jeda otomatis saat browser hilang fokus, pindah domain/tab, dan navigasi ke URL internal", async () => {
  const env = createMockWebExtensionEnv({ browserName: "chrome", hasAllUrls: true });
  let nowMs = 1_700_000_000_000;
  const bridge = new NativeBridge({ api: env.api });
  const controller = new CaptureController({
    api: env.api,
    bridge,
    nowFn: () => nowMs,
    enableSubMinuteTimer: false,
  });
  await controller.init();
  await controller.applyRuntimeConfig(makeLiveConfig({ version: 1, permissionMode: "automatic_domain" }));
  await controller.handleLocalControl("start");
  assert.equal(env.getCaptureCount(), 1);

  // 1. Browser kehilangan fokus -> jeda otomatis
  await controller.handleWindowFocusChanged(env.api.windows.WINDOW_ID_NONE);
  assert.equal(controller.captureState, "paused_unfocused");
  assert.equal(env.badgeState.text, "II");
  nowMs += 15_000;
  const unfocusedTry = await controller.captureIfEligible("timer");
  assert.equal(unfocusedTry.captured, false);
  assert.equal(unfocusedTry.reason, "window_unfocused");

  // 2. Browser fokus kembali tapi pindah ke domain lain -> idle_mismatch
  env.setActiveTab({ id: 102, windowId: 1, active: true, url: "https://youtube.com/watch?v=123" });
  await controller.handleWindowFocusChanged(1);
  assert.equal(controller.captureState, "idle_mismatch");
  assert.equal(env.badgeState.text, "");
  assert.equal(env.getCaptureCount(), 1);

  // 3. Pindah ke URL internal chrome:// -> idle_internal_url
  env.setActiveTab({ id: 103, windowId: 1, active: true, url: "chrome://extensions/" });
  await controller.evaluateActiveTab();
  assert.equal(controller.captureState, "idle_internal_url");

  // 4. Tab tidak aktif (background tab) -> ditolak
  env.setActiveTab({ id: 104, windowId: 1, active: false, url: "https://konstantaedu.com/tryout" });
  await controller.evaluateActiveTab();
  assert.equal(controller.captureState, "idle_no_active_tab");
  assert.equal(env.getCaptureCount(), 1);

  bridge.disconnect();
});

test("Local-start mode jeda saat pindah origin; tombol Pause/Stop lokal langsung bekerja", async () => {
  const env = createMockWebExtensionEnv({ browserName: "chrome", initialUrl: "https://konstantaedu.com/tryout" });
  const bridge = new NativeBridge({ api: env.api });
  const controller = new CaptureController({
    api: env.api,
    bridge,
    enableSubMinuteTimer: false,
  });
  await controller.init();
  await controller.applyRuntimeConfig(makeLiveConfig({ version: 1, permissionMode: "local_start" }));
  await controller.handleLocalControl("start");
  assert.equal(controller.captureState, "capturing");

  // Pindah ke origin berbeda (subdomain) dalam local_start -> activeTab berakhir, harus jeda
  env.setActiveTab({ id: 101, windowId: 1, active: true, url: "https://portal.konstantaedu.com/home" });
  await controller.evaluateActiveTab();
  assert.equal(controller.captureState, "paused_origin_changed");
  assert.equal(env.badgeState.text, "II");

  // Kontrol Pause & Stop lokal
  await controller.handleLocalControl("pause");
  assert.equal(controller.localSessionState, "paused");
  assert.equal(controller.captureState, "paused_local");

  await controller.handleLocalControl("stop");
  assert.equal(controller.localSessionState, "stopped");
  assert.equal(controller.captureState, "stopped_local");
  assert.equal(env.badgeState.text, "");

  bridge.disconnect();
});

test("Live config update dari Agent mengganti domain target atau mematikan capture tanpa rebuild", async () => {
  const env = createMockWebExtensionEnv({
    browserName: "chrome",
    initialUrl: "https://ujian.kampus.ac.id/sesi-1",
    hasAllUrls: true,
  });
  let nowMs = 1_700_000_000_000;
  const bridge = new NativeBridge({ api: env.api });
  const controller = new CaptureController({
    api: env.api,
    bridge,
    nowFn: () => nowMs,
    enableSubMinuteTimer: false,
  });
  await controller.init();

  // v1: target hanya konstantaedu.com -> ujian.kampus.ac.id belum cocok
  await controller.applyRuntimeConfig(makeLiveConfig({ version: 1, domain: "konstantaedu.com", permissionMode: "automatic_domain" }));
  await controller.handleLocalControl("start");
  assert.equal(controller.captureState, "idle_mismatch");
  assert.equal(env.getCaptureCount(), 0);

  // v2: admin mengganti domain target ke kampus.ac.id secara live saat aplikasi sedang dipakai!
  await controller.applyRuntimeConfig(makeLiveConfig({ version: 2, domain: "kampus.ac.id", permissionMode: "automatic_domain" }));
  assert.equal(controller.captureState, "capturing");
  assert.equal(controller.matchedDomain, "ujian.kampus.ac.id");
  const capRes = await controller.captureIfEligible("timer");
  assert.equal(capRes.captured, true);
  assert.equal(env.getCaptureCount(), 1);

  // v3: admin mengganti active_source menjadi disabled secara live -> langsung berhenti
  await controller.applyRuntimeConfig(makeLiveConfig({ version: 3, activeSource: "disabled", enabled: false }));
  assert.equal(controller.captureState, "idle_disabled");
  assert.equal(env.badgeState.text, "");

  bridge.disconnect();
});

test("Pencabutan izin browser & pemutusan Native Host langsung menghentikan capture + badge error", async () => {
  const env = createMockWebExtensionEnv({ browserName: "edge", hasAllUrls: true });
  let controller;
  const bridge = new NativeBridge({
    api: env.api,
    onConnectionChange: (connected, err) => {
      void controller?.handleHostConnectionChange(connected, err);
    },
  });
  controller = new CaptureController({
    api: env.api,
    bridge,
    enableSubMinuteTimer: false,
  });
  await controller.init();
  await controller.applyRuntimeConfig(makeLiveConfig({ version: 1, permissionMode: "automatic_domain" }));
  await controller.handleLocalControl("start");
  assert.equal(controller.captureState, "capturing");

  // Simulasikan Native Host crash/terputus
  env.getPort().simulateCrash();
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(bridge.connected, false);
  assert.equal(controller.captureState, "error_host_disconnected");
  assert.equal(env.badgeState.text, "!");

  // Hubungkan ulang & simulasikan izin <all_urls> dicabut pengguna
  bridge.connect();
  await controller.evaluateActiveTab();
  assert.equal(controller.captureState, "capturing");

  env.setHostPermission(false);
  await controller.handlePermissionsRemoved();
  assert.equal(controller.captureState, "stopped_permission_revoked");
  assert.equal(controller.localSessionState, "stopped");
  assert.equal(env.badgeState.text, "!");

  bridge.disconnect();
});

test("NativeBridge memecah gambar besar menjadi multi-chunk dengan urutan & checksum SHA-256 utuh", async () => {
  const env = createMockWebExtensionEnv({ browserName: "chrome" });
  const bridge = new NativeBridge({ api: env.api });
  bridge.connect();

  // Buat payload base64 ~4 KB lalu paksa pecah per 1024 karakter -> 4 chunk
  const rawBytes = new Uint8Array(3000);
  for (let i = 0; i < rawBytes.length; i += 1) {
    rawBytes[i] = i % 251;
  }
  const b64 = Buffer.from(rawBytes).toString("base64");
  const dataUrl = `data:image/png;base64,${b64}`;

  const res = await bridge.sendCapturedImage({
    dataUrl,
    targetFormat: "webp",
    meta: { source: "browser_tab", browser: "chrome", rule_id: "r1", origin_domain: "konstantaedu.com" },
    maxChunkChars: 1024,
  });

  assert.equal(res.ok, true);
  assert.equal(res.chunkCount, 4);

  const chunks = env.sentHostMessages.filter((m) => m.type === "capture_chunk");
  assert.equal(chunks.length, 4);
  assert.deepEqual(
    chunks.map((c) => c.chunk_index),
    [0, 1, 2, 3]
  );
  assert.equal(chunks.map((c) => c.payload).join(""), b64);
  assert.equal(chunks[0].checksum, await computeSha256Hex(rawBytes));

  bridge.disconnect();
});
