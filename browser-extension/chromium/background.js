/**
 * Service Worker MV3 untuk Google Chrome & Microsoft Edge.
 */

import { createBrowserApi } from "./shared/browser-api.js";
import { CaptureController } from "./shared/capture-controller.js";
import { NativeBridge } from "./shared/native-bridge.js";

const api = createBrowserApi();

let controller;

const bridge = new NativeBridge({
  api,
  onConfigUpdate: (msg) => {
    void controller?.applyRuntimeConfig(msg);
  },
  onControlAction: (msg) => {
    if (msg?.action === "sync_config") {
      bridge.requestConfig(controller?.runtimeConfig?.config_version || 0);
      return;
    }
    if (["start", "pause", "resume", "stop"].includes(msg?.action)) {
      void controller?.handleLocalControl(msg.action);
    }
  },
  onConnectionChange: (connected, err) => {
    void controller?.handleHostConnectionChange(connected, err);
  },
});

controller = new CaptureController({ api, bridge });

api.runtime.onInstalled?.addListener(() => {
  void controller.init();
});

api.runtime.onStartup?.addListener(() => {
  void controller.init();
});

api.runtime.onMessage?.addListener((msg, _sender, sendResponse) => {
  if (!msg || typeof msg !== "object") {
    return false;
  }

  const handle = async () => {
    await controller.init();

    switch (msg.type) {
      case "GET_STATUS":
        await controller.refreshHostPermission();
        return { ok: true, status: controller.getStatusSnapshot() };

      case "LOCAL_CONTROL": {
        const status = await controller.handleLocalControl(msg.action);
        return { ok: true, status };
      }

      case "REFRESH_PERMISSIONS": {
        await controller.refreshHostPermission();
        await controller.evaluateActiveTab({ triggerCapture: false });
        return { ok: true, status: controller.getStatusSnapshot() };
      }

      case "RECONNECT_HOST": {
        bridge.connect();
        await controller.evaluateActiveTab({ triggerCapture: false });
        return { ok: true, status: controller.getStatusSnapshot() };
      }

      default:
        return { ok: false, error: "Pesan tidak dikenal." };
    }
  };

  handle()
    .then((res) => sendResponse(res))
    .catch((err) => sendResponse({ ok: false, error: err?.message || String(err) }));

  return true; // respons async
});

void controller.init();
