/**
 * Validator skema konfigurasi runtime di sisi Browser Extension.
 * Menjamin default `browser_capture.enabled = false` dan menolak konfigurasi korup/tidak aman
 * sebelum diterapkan ke state capture.
 */

import { normalizeRuleDomain } from "./domain-matcher.js";

export const VALID_ACTIVE_SOURCES = new Set([
  "disabled",
  "browser_domain",
  "application_window",
  "desktop_mss",
]);

export const VALID_PERMISSION_MODES = new Set(["local_start", "automatic_domain"]);
export const VALID_IMAGE_FORMATS = new Set(["webp", "png"]);
export const VALID_FALLBACK_FORMATS = new Set(["png", "jpeg"]);
export const VALID_SCHEMES = new Set(["https", "http"]);
export const VALID_BROWSERS = new Set(["chrome", "edge", "firefox"]);
export const RULE_ID_REGEX = /^[a-z0-9][a-z0-9_-]{1,63}$/;

export function createDefaultBrowserCaptureConfig() {
  return {
    config_version: 0,
    active_source: "desktop_mss",
    browser_capture: {
      enabled: false,
      capture_mode: "active_tab",
      permission_mode: "local_start",
      local_session_required: true,
      pause_when_browser_unfocused: true,
      pause_when_tab_inactive: true,
      image_format: "webp",
      fallback_format: "png",
      capture_interval_seconds: 10,
      rules: [],
    },
  };
}

/**
 * Memvalidasi payload `config_update` dari Native Host / Xoose.
 * @param {object} payload
 * @returns {{ ok: boolean, errors: string[], normalized: object|null }}
 */
export function validateRuntimeConfig(payload) {
  const errors = [];
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { ok: false, errors: ["Payload konfigurasi harus berupa objek JSON."], normalized: null };
  }

  const configVersion = Number.isInteger(payload.config_version) && payload.config_version >= 0
    ? payload.config_version
    : 0;

  const activeSource = payload.active_source ?? payload.capture_policy?.active_source ?? "desktop_mss";
  if (!VALID_ACTIVE_SOURCES.has(activeSource)) {
    errors.push(`active_source tidak valid: '${String(activeSource)}'.`);
  }

  const rawBc = payload.browser_capture;
  if (!rawBc || typeof rawBc !== "object" || Array.isArray(rawBc)) {
    errors.push("Bagian 'browser_capture' wajib berupa objek.");
    return { ok: false, errors, normalized: null };
  }

  const enabled = typeof rawBc.enabled === "boolean" ? rawBc.enabled : false;
  const captureMode = rawBc.capture_mode ?? "active_tab";
  if (captureMode !== "active_tab") {
    errors.push(`capture_mode tidak didukung: '${String(captureMode)}'. Hanya 'active_tab' diizinkan.`);
  }

  const permissionMode = rawBc.permission_mode ?? "local_start";
  if (!VALID_PERMISSION_MODES.has(permissionMode)) {
    errors.push(`permission_mode tidak valid: '${String(permissionMode)}'.`);
  }

  const imageFormat = rawBc.image_format ?? "webp";
  if (!VALID_IMAGE_FORMATS.has(imageFormat)) {
    errors.push(`image_format tidak valid: '${String(imageFormat)}'.`);
  }

  const fallbackFormat = rawBc.fallback_format ?? "png";
  if (!VALID_FALLBACK_FORMATS.has(fallbackFormat)) {
    errors.push(`fallback_format tidak valid: '${String(fallbackFormat)}'.`);
  }

  const intervalSec = rawBc.capture_interval_seconds ?? 10;
  if (!Number.isInteger(intervalSec) || intervalSec < 2 || intervalSec > 3600) {
    errors.push("capture_interval_seconds harus berupa bilangan bulat antara 2 dan 3600.");
  }

  if (!Array.isArray(rawBc.rules)) {
    errors.push("browser_capture.rules harus berupa array.");
  }

  const seenIds = new Set();
  const cleanRules = [];

  if (Array.isArray(rawBc.rules)) {
    if (rawBc.rules.length > 50) {
      errors.push("Jumlah maksimum rules adalah 50.");
    }
    for (let i = 0; i < rawBc.rules.length; i += 1) {
      const r = rawBc.rules[i];
      if (!r || typeof r !== "object" || Array.isArray(r)) {
        errors.push(`rules[${i}] harus berupa objek.`);
        continue;
      }

      const id = String(r.id || "").trim();
      if (!RULE_ID_REGEX.test(id)) {
        errors.push(`rules[${i}].id tidak valid: '${id}'.`);
      } else if (seenIds.has(id)) {
        errors.push(`rules[${i}].id duplikat: '${id}'.`);
      } else {
        seenIds.add(id);
      }

      const normDomain = normalizeRuleDomain(r.domain);
      if (!normDomain) {
        errors.push(`rules[${i}].domain tidak valid: '${String(r.domain)}'.`);
      }

      const rawSchemes = Array.isArray(r.schemes) && r.schemes.length > 0 ? r.schemes : ["https"];
      const schemes = [];
      for (const s of rawSchemes) {
        const sl = String(s).toLowerCase();
        if (!VALID_SCHEMES.has(sl)) {
          errors.push(`rules[${i}].schemes mengandung skema terlarang: '${sl}'.`);
        } else if (!schemes.includes(sl)) {
          schemes.push(sl);
        }
      }

      const rawBrowsers = Array.isArray(r.browsers) && r.browsers.length > 0 ? r.browsers : ["chrome", "edge", "firefox"];
      const browsers = [];
      for (const b of rawBrowsers) {
        const bl = String(b).toLowerCase();
        if (!VALID_BROWSERS.has(bl)) {
          errors.push(`rules[${i}].browsers mengandung browser tidak dikenal: '${bl}'.`);
        } else if (!browsers.includes(bl)) {
          browsers.push(bl);
        }
      }

      cleanRules.push({
        id,
        enabled: Boolean(r.enabled),
        domain: normDomain || "",
        include_subdomains: Boolean(r.include_subdomains),
        schemes,
        browsers,
      });
    }
  }

  if (errors.length > 0) {
    return { ok: false, errors, normalized: null };
  }

  return {
    ok: true,
    errors: [],
    normalized: {
      config_version: configVersion,
      active_source: activeSource,
      browser_capture: {
        enabled,
        capture_mode: "active_tab",
        permission_mode: permissionMode,
        local_session_required: rawBc.local_session_required !== false,
        pause_when_browser_unfocused: rawBc.pause_when_browser_unfocused !== false,
        pause_when_tab_inactive: rawBc.pause_when_tab_inactive !== false,
        image_format: imageFormat,
        fallback_format: fallbackFormat,
        capture_interval_seconds: intervalSec,
        rules: cleanRules,
      },
    },
  };
}
