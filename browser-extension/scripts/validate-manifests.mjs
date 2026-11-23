import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");

function assert(cond, msg) {
  if (!cond) {
    throw new Error(msg);
  }
}

function validateManifest(variant, filePath) {
  const raw = fs.readFileSync(filePath, "utf8");
  const m = JSON.parse(raw);

  assert(m.manifest_version === 3, `${variant}: manifest_version harus 3`);
  assert(typeof m.name === "string" && m.name.toLowerCase().includes("capture"), `${variant}: nama extension harus transparan menyebutkan fungsi capture`);
  assert(Array.isArray(m.permissions), `${variant}: permissions harus array`);

  for (const reqPerm of ["activeTab", "tabs", "alarms", "storage", "nativeMessaging"]) {
    assert(m.permissions.includes(reqPerm), `${variant}: permission wajib '${reqPerm}' hilang`);
  }
  assert(!m.permissions.includes("<all_urls>"), `${variant}: <all_urls> tidak boleh wajib di permissions (harus opsional)`);

  if (variant === "chromium") {
    assert(m.background?.service_worker === "background.js", "chromium: background.service_worker harus background.js");
    assert(m.background?.type === "module", "chromium: background.type harus module");
    assert(Array.isArray(m.optional_host_permissions) && m.optional_host_permissions.includes("<all_urls>"), "chromium: optional_host_permissions harus memuat <all_urls>");
  } else if (variant === "firefox") {
    assert(Array.isArray(m.background?.scripts) && m.background.scripts.includes("background.js"), "firefox: background.scripts harus memuat background.js");
    assert(typeof m.browser_specific_settings?.gecko?.id === "string" && m.browser_specific_settings.gecko.id.length > 3, "firefox: browser_specific_settings.gecko.id wajib diisi");
    assert(Array.isArray(m.optional_permissions) && m.optional_permissions.includes("<all_urls>"), "firefox: optional_permissions harus memuat <all_urls>");
  }

  for (const sz of ["16", "32", "48", "128"]) {
    const iconRel = m.icons?.[sz];
    assert(typeof iconRel === "string", `${variant}: icons['${sz}'] hilang`);
    const iconAbs = path.join(path.dirname(filePath), iconRel);
    assert(fs.existsSync(iconAbs), `${variant}: file ikon tidak ditemukan: ${iconAbs}`);
  }

  // Pastikan tidak ada hardcoded secret/token di manifest
  assert(!/sb_secret_|xly_dev_|service_role/i.test(raw), `${variant}: terdeteksi secret terlarang di manifest`);
}

validateManifest("chromium", path.join(rootDir, "chromium", "manifest.json"));
validateManifest("firefox", path.join(rootDir, "firefox", "manifest.json"));

console.log("MANIFEST_VALIDATION_OK: chromium & firefox manifests verified.");
