/**
 * Adapter WebExtensions lintas browser (Google Chrome, Microsoft Edge, Mozilla Firefox).
 * Menyeragamkan namespace `browser.*` (Promise) vs `chrome.*` (callback/Promise)
 * tanpa mengasumsikan API ketiga browser identik.
 */

export const SUPPORTED_BROWSERS = Object.freeze(["chrome", "edge", "firefox"]);

/**
 * Mendeteksi target browser secara deterministik dari manifest/userAgent atau override eksplisit.
 * @param {object} [env]
 * @returns {"chrome"|"edge"|"firefox"}
 */
export function detectBrowser(env = globalThis) {
  if (env?.__XOOSE_BROWSER_TARGET__ && SUPPORTED_BROWSERS.includes(env.__XOOSE_BROWSER_TARGET__)) {
    return env.__XOOSE_BROWSER_TARGET__;
  }
  const ua = String(env?.navigator?.userAgent || "").toLowerCase();
  if (ua.includes("firefox")) {
    return "firefox";
  }
  if (ua.includes("edg/")) {
    return "edge";
  }
  // Fallback: jika hanya `browser.runtime.getBrowserInfo` tersedia, itu Firefox
  if (typeof env?.browser?.runtime?.getBrowserInfo === "function") {
    return "firefox";
  }
  return "chrome";
}

function promisify(targetObj, methodName, ...args) {
  const fn = targetObj?.[methodName];
  if (typeof fn !== "function") {
    return Promise.reject(new Error(`WebExtension API '${methodName}' tidak tersedia.`));
  }
  // Jika API native Promise (Firefox `browser.*` atau Chromium MV3 Promise), dukung keduanya secara aman
  try {
    const maybePromise = fn.apply(targetObj, args);
    if (maybePromise && typeof maybePromise.then === "function") {
      return maybePromise;
    }
  } catch (err) {
    // Beberapa versi Chromium lama melempar TypeError bila dipanggil tanpa callback
    if (!(err instanceof TypeError)) {
      return Promise.reject(err);
    }
  }

  return new Promise((resolve, reject) => {
    try {
      fn.call(targetObj, ...args, (result) => {
        const runtimeErr = globalThis.chrome?.runtime?.lastError;
        if (runtimeErr) {
          reject(new Error(runtimeErr.message || String(runtimeErr)));
          return;
        }
        resolve(result);
      });
    } catch (callErr) {
      reject(callErr);
    }
  });
}

/**
 * Membuat objek adapter WebExtensions yang konsisten untuk Chrome, Edge, dan Firefox.
 * Dapat menerima `rawApi` mock saat unit test.
 * @param {object} [rawApi]
 * @param {"chrome"|"edge"|"firefox"} [browserName]
 */
export function createBrowserApi(rawApi = null, browserName = null) {
  const root = rawApi || (typeof globalThis.browser !== "undefined" ? globalThis.browser : globalThis.chrome);
  const detectedBrowser = browserName || detectBrowser();

  if (!root) {
    throw new Error("Namespace WebExtensions (`browser` / `chrome`) tidak ditemukan.");
  }

  const actionApi = root.action || root.browserAction;

  return {
    browserName: detectedBrowser,
    raw: root,

    runtime: {
      get id() {
        return root.runtime?.id || "";
      },
      getManifest() {
        return typeof root.runtime?.getManifest === "function" ? root.runtime.getManifest() : {};
      },
      connectNative(hostName) {
        return root.runtime.connectNative(hostName);
      },
      sendMessage(message) {
        return promisify(root.runtime, "sendMessage", message);
      },
      onMessage: root.runtime?.onMessage,
      onInstalled: root.runtime?.onInstalled,
      onStartup: root.runtime?.onStartup,
    },

    tabs: {
      query(queryInfo) {
        return promisify(root.tabs, "query", queryInfo);
      },
      get(tabId) {
        return promisify(root.tabs, "get", tabId);
      },
      captureVisibleTab(windowId, options) {
        // WebExtensions standard captureVisibleTab hanya menerima format "png" atau "jpeg"
        const safeFormat = options?.format === "jpeg" ? "jpeg" : "png";
        const cleanOpts = { format: safeFormat };
        if (safeFormat === "jpeg" && typeof options?.quality === "number") {
          cleanOpts.quality = Math.max(10, Math.min(100, Math.round(options.quality)));
        }
        if (windowId === null || windowId === undefined) {
          return promisify(root.tabs, "captureVisibleTab", cleanOpts);
        }
        return promisify(root.tabs, "captureVisibleTab", windowId, cleanOpts);
      },
      onActivated: root.tabs?.onActivated,
      onUpdated: root.tabs?.onUpdated,
      onRemoved: root.tabs?.onRemoved,
    },

    windows: {
      WINDOW_ID_NONE: root.windows?.WINDOW_ID_NONE ?? -1,
      get(windowId) {
        return promisify(root.windows, "get", windowId);
      },
      getLastFocused(queryInfo = { populate: false }) {
        return promisify(root.windows, "getLastFocused", queryInfo);
      },
      onFocusChanged: root.windows?.onFocusChanged,
    },

    alarms: {
      create(name, alarmInfo) {
        return root.alarms?.create(name, alarmInfo);
      },
      clear(name) {
        return promisify(root.alarms, "clear", name);
      },
      get(name) {
        return promisify(root.alarms, "get", name);
      },
      onAlarm: root.alarms?.onAlarm,
    },

    storage: {
      async get(keys) {
        return promisify(root.storage.local, "get", keys);
      },
      async set(items) {
        return promisify(root.storage.local, "set", items);
      },
      async remove(keys) {
        return promisify(root.storage.local, "remove", keys);
      },
    },

    permissions: {
      contains(perms) {
        if (!root.permissions) {
          return Promise.resolve(false);
        }
        return promisify(root.permissions, "contains", perms);
      },
      request(perms) {
        if (!root.permissions) {
          return Promise.resolve(false);
        }
        return promisify(root.permissions, "request", perms);
      },
      remove(perms) {
        if (!root.permissions) {
          return Promise.resolve(false);
        }
        return promisify(root.permissions, "remove", perms);
      },
      onAdded: root.permissions?.onAdded,
      onRemoved: root.permissions?.onRemoved,
    },

    action: {
      setBadgeText(details) {
        if (!actionApi?.setBadgeText) {
          return Promise.resolve();
        }
        return promisify(actionApi, "setBadgeText", details);
      },
      setBadgeBackgroundColor(details) {
        if (!actionApi?.setBadgeBackgroundColor) {
          return Promise.resolve();
        }
        return promisify(actionApi, "setBadgeBackgroundColor", details);
      },
      setBadgeTextColor(details) {
        if (!actionApi?.setBadgeTextColor) {
          return Promise.resolve();
        }
        return promisify(actionApi, "setBadgeTextColor", details);
      },
      setTitle(details) {
        if (!actionApi?.setTitle) {
          return Promise.resolve();
        }
        return promisify(actionApi, "setTitle", details);
      },
    },
  };
}
