/**
 * Domain Matcher ketat berbasis WHATWG `new URL()` parser.
 * DILARANG menggunakan `url.includes()` atau substring matching.
 *
 * Menjamin:
 * - Normalisasi hostname lowercase, penghapusan trailing dot, penanganan port otomatis
 * - Penolakan skema internal (`chrome:`, `edge:`, `about:`, `file:`, `chrome-extension:`, `moz-extension:`, dll.)
 * - Pencocokan batas titik ketat (menolak false positive seperti `konstantaedu.com.evil.com`)
 * - Privasi metadata: tidak pernah menyertakan query string / fragment
 */

export const ALLOWED_SCHEMES = new Set(["http", "https"]);

export const DISALLOWED_SCHEMES = new Set([
  "chrome",
  "chrome-extension",
  "chrome-search",
  "chrome-untrusted",
  "edge",
  "extension",
  "about",
  "moz-extension",
  "resource",
  "jar",
  "file",
  "ftp",
  "data",
  "blob",
  "javascript",
  "view-source",
  "devtools",
]);

export const VALID_DOMAIN_REGEX =
  /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;

const IPV4_REGEX = /^\d{1,3}(?:\.\d{1,3}){3}$/;

/**
 * Normalisasi dan validasi string domain konfigurasi.
 * @param {string} rawDomain
 * @returns {string|null} domain ter-normalisasi atau null jika invalid
 */
export function normalizeRuleDomain(rawDomain) {
  if (typeof rawDomain !== "string") {
    return null;
  }
  const cleaned = rawDomain.trim().toLowerCase().replace(/\.+$/, "");
  if (!cleaned || cleaned.length > 253) {
    return null;
  }
  if (
    cleaned.includes("*") ||
    cleaned.includes("/") ||
    cleaned.includes(":") ||
    cleaned.includes(" ") ||
    cleaned.includes("..")
  ) {
    return null;
  }
  if (IPV4_REGEX.test(cleaned)) {
    return null;
  }
  if (!VALID_DOMAIN_REGEX.test(cleaned)) {
    return null;
  }
  return cleaned;
}

/**
 * Mem-parse dan menormalisasi URL tab browser secara aman.
 * @param {string} rawUrl
 * @returns {{ ok: boolean, reason?: string, scheme?: string, hostname?: string }}
 */
export function parseTabUrl(rawUrl) {
  if (typeof rawUrl !== "string") {
    return { ok: false, reason: "invalid_url" };
  }
  const trimmed = rawUrl.trim();
  if (!trimmed || trimmed.length > 4096) {
    return { ok: false, reason: "invalid_url" };
  }

  let parsed;
  try {
    parsed = new URL(trimmed);
  } catch {
    return { ok: false, reason: "invalid_url" };
  }

  const scheme = parsed.protocol.replace(/:$/, "").toLowerCase();
  if (DISALLOWED_SCHEMES.has(scheme) || !ALLOWED_SCHEMES.has(scheme)) {
    return { ok: false, reason: "disallowed_scheme" };
  }

  const hostname = parsed.hostname.toLowerCase().trim().replace(/\.+$/, "");
  if (!hostname || hostname.includes(" ") || hostname.includes("..")) {
    return { ok: false, reason: "invalid_hostname" };
  }
  // Tolak IPv6 bracketed atau IPv4 mentah pada pencocokan domain web
  if (hostname.startsWith("[") || hostname.endsWith("]") || IPV4_REGEX.test(hostname)) {
    return { ok: false, reason: "ip_not_allowed" };
  }

  return {
    ok: true,
    scheme,
    hostname,
  };
}

/**
 * Mengevaluasi satu hostname terhadap satu domain rule.
 * @param {string} hostname - hostname sudah dinormalisasi lowercase tanpa trailing dot/port
 * @param {string} ruleDomain - domain rule sudah dinormalisasi
 * @param {boolean} includeSubdomains
 * @returns {boolean}
 */
export function isDomainMatch(hostname, ruleDomain, includeSubdomains = true) {
  if (!hostname || !ruleDomain) {
    return false;
  }
  if (hostname === ruleDomain) {
    return true;
  }
  if (includeSubdomains === true) {
    return hostname.endsWith("." + ruleDomain);
  }
  return false;
}

/**
 * Mencocokkan URL tab aktif terhadap daftar rule untuk browser tertentu.
 * Mengembalikan rule pertama yang cocok beserta metadata domain bersih (tanpa query/fragment).
 *
 * @param {string} rawUrl
 * @param {Array<object>} rules
 * @param {"chrome"|"edge"|"firefox"} browserName
 * @returns {{
 *   matched: boolean,
 *   reason: string,
 *   rule: object|null,
 *   rule_id: string|null,
 *   origin_domain: string|null,
 *   scheme: string|null
 * }}
 */
export function matchUrlAgainstRules(rawUrl, rules = [], browserName = "chrome") {
  const parsed = parseTabUrl(rawUrl);
  if (!parsed.ok) {
    return {
      matched: false,
      reason: parsed.reason || "invalid_url",
      rule: null,
      rule_id: null,
      origin_domain: null,
      scheme: null,
    };
  }

  const normalizedBrowser = String(browserName || "").toLowerCase();
  const list = Array.isArray(rules) ? rules : [];

  for (const rule of list) {
    if (!rule || rule.enabled !== true) {
      continue;
    }

    const browsers = Array.isArray(rule.browsers)
      ? rule.browsers.map((b) => String(b).toLowerCase())
      : ["chrome", "edge", "firefox"];
    if (!browsers.includes(normalizedBrowser)) {
      continue;
    }

    const schemes =
      Array.isArray(rule.schemes) && rule.schemes.length > 0
        ? rule.schemes.map((s) => String(s).toLowerCase())
        : ["https"];
    if (!schemes.includes(parsed.scheme)) {
      continue;
    }

    const ruleDomain = normalizeRuleDomain(rule.domain);
    if (!ruleDomain) {
      continue;
    }

    if (isDomainMatch(parsed.hostname, ruleDomain, rule.include_subdomains === true)) {
      return {
        matched: true,
        reason: "matched",
        rule,
        rule_id: String(rule.id || ""),
        origin_domain: parsed.hostname,
        scheme: parsed.scheme,
      };
    }
  }

  return {
    matched: false,
    reason: "domain_mismatch",
    rule: null,
    rule_id: null,
    origin_domain: null,
    scheme: parsed.scheme,
  };
}
