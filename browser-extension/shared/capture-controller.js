/**
 * CaptureController: State machine transparan untuk Browser Domain Capture.
 *
 * Menegakkan:
 * - Active tab only (`tabs.captureVisibleTab()`) — tidak pernah menangkap tab background
 * - Default `enabled: false` & mode izin `local_start` (`activeTab`)
 * - Mode opsional `automatic_domain` hanya berjalan setelah persetujuan `<all_urls>`
 * - Auto-pause saat browser unfocused, pindah tab, pindah domain, atau izin dicabut
 * - Pembaruan aturan domain live saat runtime (config_update) tanpa rebuild/reinstall
 * - Indikator badge minimalis + kontrol lokal Start / Pause / Resume / Stop
 * - Tahan lifecycle MV3 service worker (persistensi state di `storage.local` + `alarms` watchdog)
 */

import { createDefaultBrowserCaptureConfig, validateRuntimeConfig } from "./config-validator.js";
import { matchUrlAgainstRules } from "./domain-matcher.js";

export const STORAGE_STATE_KEY = "xoose_capture_state_v1";
export const CAPTURE_ALARM_NAME = "xoose_capture_watchdog";

export const BADGE_STYLES = Object.freeze({
  capturing: { text: "ON", color: "#10B981", title: "Xoose–LoveYou Capture: Aktif" },
  paused: { text: "II", color: "#F59E0B", title: "Xoose–LoveYou Capture: Dijeda" },
  error: { text: "!", color: "#EF4444", title: "Xoose–LoveYou Capture: Terputus / Error" },
  idle: { text: "", color: "#6B7280", title: "Xoose–LoveYou Capture: Siaga" },
});

export class CaptureController {
  /**
   * @param {object} opts
   * @param {object} opts.api - adapter dari createBrowserApi()
   * @param {object} opts.bridge - instance NativeBridge
   * @param {function} [opts.nowFn] - sumber waktu deterministik (default Date.now)
   * @param {boolean} [opts.enableSubMinuteTimer] - timer interval presisi ketika SW aktif
   */
  constructor({ api, bridge, nowFn = () => Date.now(), enableSubMinuteTimer = true }) {
    this.api = api;
    this.bridge = bridge;
    this.nowFn = nowFn;
    this.enableSubMinuteTimer = enableSubMinuteTimer;

    this.runtimeConfig = createDefaultBrowserCaptureConfig();

    // State sesi lokal & runtime
    this.localSessionState = "stopped"; // "running" | "paused" | "stopped"
    this.captureState = "idle_disabled";
    this.hasAllUrlsPermission = false;
    this.windowFocused = true;
    this.activeWindowId = null;
    this.activeTabId = null;
    this.localStartTabId = null;
    this.localStartDomain = null;
    this.activeRuleId = null;
    this.matchedDomain = null;
    this.capturesSent = 0;
    this.lastCaptureAt = null;
    this.lastCaptureTs = 0;
    this.lastError = null;

    this._captureInFlight = false;
    this._tickTimer = null;
    this._initialized = false;
  }

  async init() {
    if (this._initialized) {
      return;
    }
    this._initialized = true;
    await this._restoreState();
    await this.refreshHostPermission();
    this._attachListeners();
    this.bridge.connect();
    await this.evaluateActiveTab({ triggerCapture: false });
  }

  _attachListeners() {
    this.api.tabs.onActivated?.addListener(() => {
      void this.evaluateActiveTab({ triggerCapture: false });
    });

    this.api.tabs.onUpdated?.addListener((tabId, changeInfo, tab) => {
      if (tab?.active && (changeInfo.url || changeInfo.status === "complete")) {
        void this.evaluateActiveTab({ triggerCapture: false });
      }
    });

    this.api.tabs.onRemoved?.addListener((tabId) => {
      if (tabId === this.localStartTabId) {
        this.localStartTabId = null;
        this.localStartDomain = null;
        if (this.getEffectivePermissionMode() === "local_start" && this.localSessionState === "running") {
          this.localSessionState = "paused";
        }
      }
      if (tabId === this.activeTabId) {
        this.activeTabId = null;
        this.activeRuleId = null;
        this.matchedDomain = null;
      }
      void this.evaluateActiveTab({ triggerCapture: false });
    });

    this.api.windows.onFocusChanged?.addListener((windowId) => {
      void this.handleWindowFocusChanged(windowId);
    });

    this.api.alarms.onAlarm?.addListener((alarm) => {
      if (alarm?.name === CAPTURE_ALARM_NAME) {
        if (!this.bridge.connected) {
          this.bridge.connect();
        } else {
          this.bridge.requestConfig(this.runtimeConfig.config_version);
        }
        void this.captureIfEligible("alarm");
      }
    });

    this.api.permissions.onAdded?.addListener(() => {
      void this.refreshHostPermission().then(() => this.evaluateActiveTab({ triggerCapture: false }));
    });

    this.api.permissions.onRemoved?.addListener(() => {
      void this.handlePermissionsRemoved();
    });
  }

  getEffectivePermissionMode() {
    const requested = this.runtimeConfig.browser_capture.permission_mode || "local_start";
    if (requested === "automatic_domain" && this.hasAllUrlsPermission) {
      return "automatic_domain";
    }
    return "local_start";
  }

  isBrowserCapturePolicyActive() {
    return (
      this.runtimeConfig.active_source === "browser_domain" &&
      this.runtimeConfig.browser_capture.enabled === true
    );
  }

  async refreshHostPermission() {
    try {
      this.hasAllUrlsPermission = Boolean(
        await this.api.permissions.contains({ origins: ["<all_urls>"] })
      );
    } catch {
      this.hasAllUrlsPermission = false;
    }
    return this.hasAllUrlsPermission;
  }

  async handlePermissionsRemoved() {
    const hadPermission = this.hasAllUrlsPermission;
    await this.refreshHostPermission();
    if (hadPermission && !this.hasAllUrlsPermission) {
      this.captureState = "stopped_permission_revoked";
      this.localSessionState = "stopped";
      this.lastError = "Izin akses situs browser dicabut oleh pengguna.";
      this._stopTimers();
      await this._syncUiAndReport();
    }
  }

  async handleWindowFocusChanged(windowId) {
    if (windowId === this.api.windows.WINDOW_ID_NONE) {
      this.windowFocused = false;
      if (this.runtimeConfig.browser_capture.pause_when_browser_unfocused) {
        this.captureState = "paused_unfocused";
        this._clearSubMinuteTimer();
        await this._syncUiAndReport();
      }
      return;
    }
    this.windowFocused = true;
    this.activeWindowId = windowId;
    await this.evaluateActiveTab({ triggerCapture: false });
  }

  /**
   * Menerapkan konfigurasi runtime terbaru yang diterima live dari LoveYou Agent / Xoose.
   * @param {object} configMsg
   */
  async applyRuntimeConfig(configMsg) {
    const validation = validateRuntimeConfig(configMsg);
    if (!validation.ok || !validation.normalized) {
      this.lastError = `Konfigurasi ditolak: ${validation.errors.join("; ")}`;
      await this._syncUiAndReport();
      return { ok: false, errors: validation.errors };
    }

    this.runtimeConfig = validation.normalized;
    this.lastError = null;

    if (!this.isBrowserCapturePolicyActive()) {
      this.captureState = "idle_disabled";
      this.activeRuleId = null;
      this.matchedDomain = null;
      this._stopTimers();
      await this._persistState();
      await this._syncUiAndReport();
      return { ok: true, config_version: this.runtimeConfig.config_version };
    }

    // Jika mode otomatis sudah mendapat izin <all_urls> dan user tidak menekan Stop lokal secara eksplisit
    if (
      this.getEffectivePermissionMode() === "automatic_domain" &&
      !this.runtimeConfig.browser_capture.local_session_required &&
      this.localSessionState === "stopped"
    ) {
      this.localSessionState = "running";
    }

    await this._persistState();
    await this.evaluateActiveTab({ triggerCapture: false });
    return { ok: true, config_version: this.runtimeConfig.config_version };
  }

  /**
   * Menangani aksi kontrol lokal (dari popup Extension atau LoveYou Tray via Native Host).
   * @param {"start"|"pause"|"resume"|"stop"} action
   */
  async handleLocalControl(action) {
    const clean = String(action || "").toLowerCase();

    if (clean === "stop") {
      this.localSessionState = "stopped";
      this.localStartTabId = null;
      this.localStartDomain = null;
      this.captureState = "stopped_local";
      this._stopTimers();
      await this._persistState();
      await this._syncUiAndReport();
      return this.getStatusSnapshot();
    }

    if (clean === "pause") {
      if (this.localSessionState !== "stopped") {
        this.localSessionState = "paused";
      }
      this.captureState = "paused_local";
      this._stopTimers();
      await this._persistState();
      await this._syncUiAndReport();
      return this.getStatusSnapshot();
    }

    if (clean === "start" || clean === "resume") {
      this.localSessionState = "running";
      this.lastError = null;
      // Catat tab & domain tempat user mengklik Start untuk mode activeTab (local_start)
      const tab = await this._queryActiveTab();
      if (tab) {
        this.localStartTabId = tab.id ?? null;
        const match = matchUrlAgainstRules(
          tab.url || "",
          this.runtimeConfig.browser_capture.rules,
          this.api.browserName
        );
        this.localStartDomain = match.matched ? match.origin_domain : null;
      }
      await this._persistState();
      await this.evaluateActiveTab({ triggerCapture: true });
      return this.getStatusSnapshot();
    }

    return this.getStatusSnapshot();
  }

  async handleHostConnectionChange(connected, errorMsg = null) {
    if (!connected) {
      this.lastError = errorMsg || "Native host terputus.";
      this.captureState = "error_host_disconnected";
      this._clearSubMinuteTimer();
      await this._syncUiAndReport();
      return;
    }
    this.lastError = null;
    await this.evaluateActiveTab({ triggerCapture: false });
  }

  async _queryActiveTab() {
    try {
      const tabs = await this.api.tabs.query({ active: true, lastFocusedWindow: true });
      if (Array.isArray(tabs) && tabs.length > 0) {
        return tabs[0];
      }
    } catch {
      // fallback di bawah
    }
    try {
      const tabs = await this.api.tabs.query({ active: true, currentWindow: true });
      return Array.isArray(tabs) && tabs.length > 0 ? tabs[0] : null;
    } catch {
      return null;
    }
  }

  /**
   * Mengevaluasi apakah tab aktif saat ini memenuhi seluruh syarat capture.
   */
  async evaluateActiveTab({ triggerCapture = false } = {}) {
    if (!this.isBrowserCapturePolicyActive()) {
      this.captureState = "idle_disabled";
      this.activeRuleId = null;
      this.matchedDomain = null;
      this._stopTimers();
      await this._syncUiAndReport();
      return { eligible: false, reason: "policy_disabled" };
    }

    if (!this.bridge.connected) {
      this.captureState = "error_host_disconnected";
      this._clearSubMinuteTimer();
      await this._syncUiAndReport();
      return { eligible: false, reason: "host_disconnected" };
    }

    if (this.localSessionState === "stopped") {
      this.captureState = "stopped_local";
      this._stopTimers();
      await this._syncUiAndReport();
      return { eligible: false, reason: "local_stopped" };
    }

    if (this.localSessionState === "paused") {
      this.captureState = "paused_local";
      this._stopTimers();
      await this._syncUiAndReport();
      return { eligible: false, reason: "local_paused" };
    }

    if (this.runtimeConfig.browser_capture.pause_when_browser_unfocused && !this.windowFocused) {
      this.captureState = "paused_unfocused";
      this._clearSubMinuteTimer();
      await this._syncUiAndReport();
      return { eligible: false, reason: "window_unfocused" };
    }

    const tab = await this._queryActiveTab();
    if (!tab || !tab.active) {
      this.captureState = "idle_no_active_tab";
      this.activeTabId = null;
      this.activeRuleId = null;
      this.matchedDomain = null;
      this._clearSubMinuteTimer();
      await this._syncUiAndReport();
      return { eligible: false, reason: "no_active_tab" };
    }

    this.activeTabId = tab.id ?? null;
    this.activeWindowId = tab.windowId ?? this.activeWindowId;

    const match = matchUrlAgainstRules(
      tab.url || "",
      this.runtimeConfig.browser_capture.rules,
      this.api.browserName
    );

    if (!match.matched) {
      this.activeRuleId = null;
      this.matchedDomain = null;
      this.captureState = match.reason === "disallowed_scheme" ? "idle_internal_url" : "idle_mismatch";
      this._clearSubMinuteTimer();
      await this._syncUiAndReport();
      return { eligible: false, reason: match.reason };
    }

    // Pada mode local_start (activeTab), jika pindah tab atau pindah origin, izin activeTab berakhir -> jeda
    const mode = this.getEffectivePermissionMode();
    if (mode === "local_start") {
      if (
        (this.localStartTabId !== null && tab.id !== this.localStartTabId) ||
        (this.localStartDomain !== null && match.origin_domain !== this.localStartDomain)
      ) {
        this.activeRuleId = null;
        this.matchedDomain = null;
        this.captureState = "paused_origin_changed";
        this._clearSubMinuteTimer();
        await this._syncUiAndReport();
        return { eligible: false, reason: "local_start_origin_changed" };
      }
      // Kunci tab & domain awal jika belum tercatat
      if (this.localStartTabId === null) {
        this.localStartTabId = tab.id ?? null;
      }
      if (this.localStartDomain === null) {
        this.localStartDomain = match.origin_domain;
      }
    }

    this.activeRuleId = match.rule_id;
    this.matchedDomain = match.origin_domain;
    this.captureState = "capturing";
    this._ensureScheduling();
    await this._syncUiAndReport();

    if (triggerCapture) {
      await this.captureIfEligible("immediate");
    }

    return { eligible: true, tab, match };
  }

  /**
   * Menjalankan 1 kali pengambilan gambar tab aktif bila seluruh guard terpenuhi.
   */
  async captureIfEligible(trigger = "timer") {
    if (this._captureInFlight) {
      return { captured: false, reason: "in_flight" };
    }

    const evalRes = await this.evaluateActiveTab({ triggerCapture: false });
    if (!evalRes.eligible) {
      return { captured: false, reason: evalRes.reason };
    }

    const intervalMs = Math.max(2000, this.runtimeConfig.browser_capture.capture_interval_seconds * 1000);
    const now = this.nowFn();
    if (trigger !== "immediate" && this.lastCaptureTs > 0 && now - this.lastCaptureTs < intervalMs - 250) {
      return { captured: false, reason: "interval_not_elapsed" };
    }

    this._captureInFlight = true;
    try {
      const dataUrl = await this.api.tabs.captureVisibleTab(evalRes.tab.windowId, {
        format: "png",
      });

      const capturedAtIso = new Date(this.nowFn()).toISOString();
      const sendRes = await this.bridge.sendCapturedImage({
        dataUrl,
        targetFormat: this.runtimeConfig.browser_capture.image_format || "webp",
        meta: {
          source: "browser_tab",
          browser: this.api.browserName,
          rule_id: evalRes.match.rule_id,
          origin_domain: evalRes.match.origin_domain,
          captured_at: capturedAtIso,
        },
      });

      if (!sendRes.ok) {
        this.lastError = sendRes.error || "Gagal mengirim gambar ke Native Host.";
        await this._syncUiAndReport();
        return { captured: false, reason: "send_failed", error: this.lastError };
      }

      this.capturesSent += 1;
      this.lastCaptureTs = this.nowFn();
      this.lastCaptureAt = capturedAtIso;
      this.lastError = null;
      await this._persistState();
      await this._syncUiAndReport();

      return {
        captured: true,
        captureId: sendRes.captureId,
        rule_id: evalRes.match.rule_id,
        origin_domain: evalRes.match.origin_domain,
        checksum: sendRes.checksum,
      };
    } catch (err) {
      const msg = err?.message || String(err);
      this.lastError = msg;
      // Jika izin activeTab/host ditolak browser saat captureVisibleTab()
      if (/permission|activeTab|cannot be edited|hosts/i.test(msg)) {
        this.captureState = "stopped_permission_revoked";
        this._clearSubMinuteTimer();
      }
      await this._syncUiAndReport();
      return { captured: false, reason: "capture_error", error: msg };
    } finally {
      this._captureInFlight = false;
    }
  }

  _ensureScheduling() {
    const intervalSec = Math.max(2, this.runtimeConfig.browser_capture.capture_interval_seconds || 10);
    // Watchdog alarm tahan penghentian MV3 service worker (min period Chrome/Edge 0.5 menit)
    const periodMinutes = Math.max(0.5, intervalSec / 60);
    try {
      this.api.alarms.create(CAPTURE_ALARM_NAME, { periodInMinutes: periodMinutes });
    } catch {
      // abaikan bila lingkungan mock tidak membutuhkan alarm
    }

    if (this.enableSubMinuteTimer && !this._tickTimer) {
      this._tickTimer = setInterval(() => {
        void this.captureIfEligible("timer");
      }, intervalSec * 1000);
    }
  }

  _clearSubMinuteTimer() {
    if (this._tickTimer) {
      clearInterval(this._tickTimer);
      this._tickTimer = null;
    }
  }

  _stopTimers() {
    this._clearSubMinuteTimer();
    try {
      void this.api.alarms.clear(CAPTURE_ALARM_NAME);
    } catch {
      // abaikan
    }
  }

  getBadgeDescriptor() {
    if (this.captureState === "capturing") {
      return BADGE_STYLES.capturing;
    }
    if (
      this.captureState === "paused_local" ||
      this.captureState === "paused_unfocused" ||
      this.captureState === "paused_origin_changed"
    ) {
      return BADGE_STYLES.paused;
    }
    if (
      this.captureState === "error_host_disconnected" ||
      this.captureState === "stopped_permission_revoked"
    ) {
      return BADGE_STYLES.error;
    }
    return BADGE_STYLES.idle;
  }

  getStatusSnapshot() {
    return {
      browser: this.api.browserName,
      extension_connected: this.bridge.connected,
      active_source: this.runtimeConfig.active_source,
      policy_enabled: this.isBrowserCapturePolicyActive(),
      permission_mode: this.getEffectivePermissionMode(),
      requested_permission_mode: this.runtimeConfig.browser_capture.permission_mode,
      has_host_permission: this.hasAllUrlsPermission,
      local_session_state: this.localSessionState,
      capture_state: this.captureState,
      active_rule_id: this.activeRuleId,
      matched_domain: this.matchedDomain,
      rules_count: this.runtimeConfig.browser_capture.rules.filter((r) => r.enabled).length,
      interval_seconds: this.runtimeConfig.browser_capture.capture_interval_seconds,
      image_format: this.runtimeConfig.browser_capture.image_format,
      config_version: this.runtimeConfig.config_version,
      captures_sent: this.capturesSent,
      last_capture_at: this.lastCaptureAt,
      last_error: this.lastError,
    };
  }

  async _syncUiAndReport() {
    const badge = this.getBadgeDescriptor();
    try {
      await this.api.action.setBadgeText({ text: badge.text });
      await this.api.action.setBadgeBackgroundColor({ color: badge.color });
      await this.api.action.setBadgeTextColor({ color: "#FFFFFF" });
      await this.api.action.setTitle({ title: badge.title });
    } catch {
      // beberapa browser/versi tidak mendukung setBadgeTextColor
    }

    if (this.bridge.connected) {
      this.bridge.sendStatusReport(this.getStatusSnapshot());
    }
  }

  async _persistState() {
    try {
      await this.api.storage.set({
        [STORAGE_STATE_KEY]: {
          runtimeConfig: this.runtimeConfig,
          localSessionState: this.localSessionState,
          capturesSent: this.capturesSent,
          lastCaptureAt: this.lastCaptureAt,
        },
      });
    } catch {
      // abaikan bila storage tidak tersedia
    }
  }

  async _restoreState() {
    try {
      const stored = await this.api.storage.get(STORAGE_STATE_KEY);
      const saved = stored?.[STORAGE_STATE_KEY];
      if (!saved || typeof saved !== "object") {
        return;
      }
      if (saved.runtimeConfig) {
        const res = validateRuntimeConfig(saved.runtimeConfig);
        if (res.ok && res.normalized) {
          this.runtimeConfig = res.normalized;
        }
      }
      if (["running", "paused", "stopped"].includes(saved.localSessionState)) {
        this.localSessionState = saved.localSessionState;
      }
      if (typeof saved.capturesSent === "number") {
        this.capturesSent = saved.capturesSent;
      }
      if (typeof saved.lastCaptureAt === "string") {
        this.lastCaptureAt = saved.lastCaptureAt;
      }
    } catch {
      // gunakan default aman bila storage gagal dibaca
    }
  }
}
