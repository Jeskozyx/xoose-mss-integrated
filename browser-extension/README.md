# Xoose–LoveYou Browser Extension

Ekstensi WebExtensions transparan untuk menangkap **isi tab browser aktif saja** (`tabs.captureVisibleTab()`) berdasarkan aturan domain runtime dari dashboard Xoose, mendukung **Google Chrome**, **Microsoft Edge**, dan **Mozilla Firefox**.

## Struktur

- `shared/` — Codebase bersama (`browser-api.js`, `domain-matcher.js`, `capture-controller.js`, `native-bridge.js`, `config-validator.js`).
- `chromium/` — Manifest V3 (`service_worker`) untuk Google Chrome dan Microsoft Edge.
- `firefox/` — Manifest V3 Variant Gecko (`background.scripts` + `browser_specific_settings.gecko.id`) untuk Mozilla Firefox.
- `scripts/` — Script PowerShell untuk build & packaging (`build-chromium.ps1`, `build-firefox.ps1`, `package-all.ps1`) dan `validate-manifests.mjs`.
- `tests/` — Automated tests (`domain-matcher.test.js`, `capture-policy.test.js`).

## Cara Menjalankan Test & Build

```powershell
cd "D:\KULIAH\KODINGAN\xoose-loveyou\browser-extension"
npm run lint
npm test
powershell -ExecutionPolicy Bypass -File ".\scripts\package-all.ps1"
```

## Memuat di Browser (Mode Pengembangan)

- **Google Chrome:** Buka `chrome://extensions` → aktifkan *Developer Mode* → **Load Unpacked** → pilih `dist\chromium`.
- **Microsoft Edge:** Buka `edge://extensions` → aktifkan *Developer Mode* → **Load Unpacked** → pilih `dist\chromium`.
- **Mozilla Firefox:** Buka `about:debugging#/runtime/this-firefox` → **Load Temporary Add-on** → pilih `dist\firefox\manifest.json`.

## Transparansi & Mode Izin

- **Local-Start Mode (Default):** Menggunakan `activeTab`; pengguna menekan **Mulai** pada popup ekstensi di tab target.
- **Automatic Domain Mode (Opsional):** Membutuhkan persetujuan eksplisit `<all_urls>` melalui tombol **Izinkan Mode Otomatis** di popup.
- Badge minimalis (`ON` / `II` / `!`) dan tombol lokal **Jeda** & **Hentikan** selalu tersedia.
