# Panduan Instalasi & Uninstall Native Messaging + Browser Extension (Windows)

**Milestone:** BC-6 — Builder & Installer  
**Root Integrasi Aktual:** `D:\KULIAH\KODINGAN\xoose-loveyou`  
**Host Name Resmi:** `com.xoose.loveyou.host`

---

## 1. Membangun Paket Distribusi (`xoose_builder`)

Jalankan perintah berikut untuk membundel **Browser Extension** (Chromium & Firefox), **Native Messaging Host** (`PyInstaller --onedir` stdio-safe), template manifest 3 browser, serta script installer/uninstaller Windows dalam satu direktori siap distribusi:

```powershell
cd "D:\KULIAH\KODINGAN\xoose-loveyou\builder"
python -m xoose_builder.cli bundle-browser-capture --bundle-id v1
```

Hasil paket akan tersedia di `D:\KULIAH\KODINGAN\xoose-loveyou\builds\browser-capture\bundle_v1\`:
- `extensions\chromium\` & `extensions\xoose-capture-chromium.zip` (untuk **Google Chrome** & **Microsoft Edge**)
- `extensions\firefox\` & `extensions\xoose-capture-firefox.zip` (untuk **Mozilla Firefox**)
- `native-host\dist\xoose-native-host\xoose-native-host.exe` (binary Native Host `onedir`)
- `native-host\host_manifest\{chrome,edge,firefox}.template.json`
- `native-host\install\install-host.ps1` & `uninstall-host.ps1`
- `bundle-manifest.json` (daftar artefak lengkap dengan checksum SHA-256)

---

## 2. Memuat Browser Extension (Per Browser)

### A. Google Chrome
1. Buka `chrome://extensions`.
2. Aktifkan **Developer mode** di pojok kanan atas.
3. Klik **Load unpacked** lalu pilih folder `extensions\chromium` (atau `D:\KULIAH\KODINGAN\xoose-loveyou\browser-extension\dist\chromium`).
4. **Salin Extension ID** (32 karakter huruf `a`–`p`) yang tampil di kartu ekstensi **Xoose-LoveYou Browser Capture**.

### B. Microsoft Edge
1. Buka `edge://extensions`.
2. Aktifkan **Developer mode** di panel kiri.
3. Klik **Load unpacked** lalu pilih folder `extensions\chromium`.
4. **Salin Extension ID** (32 karakter) milik Edge.

### C. Mozilla Firefox
1. Buka `about:debugging#/runtime/this-firefox`.
2. Klik **Load Temporary Add-on…** lalu pilih `extensions\firefox\manifest.json`.
3. Add-on ID Gecko sudah ditetapkan di manifest: `loveyou-capture@xoose.local`.

---

## 3. Registrasi Native Messaging Host (`HKCU` Registry)

### Mode Produksi / Bundled (`xoose-native-host.exe` onedir)
```powershell
powershell -ExecutionPolicy Bypass -File "D:\KULIAH\KODINGAN\xoose-loveyou\builds\browser-capture\bundle_v1\native-host\install\install-host.ps1" `
  -ChromeExtensionId "<PASTE_32_CHAR_CHROME_ID>" `
  -EdgeExtensionId "<PASTE_32_CHAR_EDGE_ID>" `
  -FirefoxAddonId "loveyou-capture@xoose.local" `
  -HostExecutable "D:\KULIAH\KODINGAN\xoose-loveyou\builds\browser-capture\bundle_v1\native-host\dist\xoose-native-host\xoose-native-host.exe"
```

### Mode Pengembangan (Python langsung ke `host.py`)
```powershell
powershell -ExecutionPolicy Bypass -File "D:\KULIAH\KODINGAN\xoose-loveyou\native-host\install\install-host.ps1" `
  -ChromeExtensionId "<PASTE_32_CHAR_CHROME_ID>" `
  -EdgeExtensionId "<PASTE_32_CHAR_EDGE_ID>" `
  -FirefoxAddonId "loveyou-capture@xoose.local"
```

### Registry Key HKCU yang Didaftarkan (Per-User, Tanpa Hak Admin)

| Browser | Registry Key Windows (`HKCU`) | Kunci Otorisasi Manifest |
| :--- | :--- | :--- |
| **Google Chrome** | `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.xoose.loveyou.host` | `"allowed_origins": ["chrome-extension://<CHROME_ID>/"]` |
| **Microsoft Edge** | `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.xoose.loveyou.host` | `"allowed_origins": ["chrome-extension://<EDGE_ID>/"]` |
| **Mozilla Firefox** | `HKCU\Software\Mozilla\NativeMessagingHosts\com.xoose.loveyou.host` | `"allowed_extensions": ["loveyou-capture@xoose.local"]` |

File manifest tergenerasi disimpan terisolasi di `%LOCALAPPDATA%\XooseLoveYouAgent\native-host\`.

---

## 4. Verifikasi Koneksi

1. Jalankan **LoveYou** (`loveyou.exe` atau `python backend/screenshot_service.py`) yang terhubung ke Xoose Control Plane.
2. Klik ikon **Xoose-LoveYou Browser Capture** di toolbar browser.
3. Pastikan status **Native Host** menampilkan **`Terhubung`** (jika sebelumnya `Terputus`, klik tautan **`Hubungkan`** pada popup).
4. Di dashboard Xoose (`/remote/capture-rules`), verifikasi panel **Status Live Extension & Agent** menampilkan **`Extension Terhubung`**.

---

## 5. Uninstall & Rollback Bersih

Untuk mencabut registrasi Native Messaging Host tanpa menyentuh file pribadi pengguna:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\KULIAH\KODINGAN\xoose-loveyou\native-host\install\uninstall-host.ps1"
```

Kemudian hapus ekstensi dari browser:
- **Chrome:** `chrome://extensions` → klik **Remove** pada *Xoose-LoveYou Browser Capture*.
- **Edge:** `edge://extensions` → klik **Remove**.
- **Firefox:** `about:debugging` / `about:addons` → klik **Remove**.
