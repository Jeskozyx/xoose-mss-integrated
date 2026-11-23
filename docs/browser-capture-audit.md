# Milestone BC-0 — Audit Browser Capture & Live Target Selection

**Tanggal Audit:** 23 November 2026  
**Status:** Selesai (**Read-Only Audit — Tanpa Perubahan Kode Aplikasi**)  
**Dokumen Referensi:** [specific_screen_xoose_loveyou.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/specific_screen_xoose_loveyou.md) & [Specific Screen Xoose-LoveYou.pdf](file:///D:/KULIAH/KODINGAN/xoose-loveyou/Specific%20Screen%20Xoose-LoveYou.pdf)  
**Audit Sebelumnya:** [docs/audit.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/docs/audit.md), [docs/remote-service-audit.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/docs/remote-service-audit.md)

---

## 1. Verifikasi Lokasi Proyek, Status Git, & Sinkronisasi GitHub

### 1.1 Perbandingan Path Dokumen vs Path Aktual di Disk (TEMUAN #1)

| Komponen | Path di Dokumen Spesifikasi | Path Aktual Terverifikasi | Status |
| :--- | :--- | :--- | :--- |
| **Root Integrasi** | `D:\KULIAH KODINGAN\xoose-loveyou` *(spasi)* | `D:\KULIAH\KODINGAN\xoose-loveyou` *(backslash)* | Path spasi: **TIDAK ADA** (`False`); Path aktual: **ADA** (`True`) |
| **Source LoveYou** | `D:\KULIAH KODINGAN\screenshotusingpy` *(spasi)* | `D:\KULIAH\KODINGAN\screenshotusingpy` *(backslash)* | Path aktual: **ADA** (`True`) |
| **Laravel Xoose** | `D:\laragon\www\xoose` | `D:\laragon\www\xoose` | **ADA** (`True`) |
| **Browser Extension** | `...\xoose-loveyou\browser-extension\` | Belum ada | Akan dibuat di Milestone **BC-2** |
| **Native Host** | `...\xoose-loveyou\native-host\` | Belum ada | Akan dibuat di Milestone **BC-3** |

> **Kesimpulan Path:** Seluruh script, manifest, konfigurasi Laravel, dan dokumentasi di milestone BC-1 s.d. BC-8 wajib menggunakan path aktual `D:\KULIAH\KODINGAN\xoose-loveyou` dan `D:\KULIAH\KODINGAN\screenshotusingpy` (tetap di bawah `D:\KULIAH\KODINGAN`, tidak dipindahkan ke `D:\laragon\www`).

### 1.2 Status Git Lokal vs Remote GitHub

Seluruh 3 repository telah diverifikasi menggunakan `git status`, `git rev-parse HEAD`, dan `git ls-remote origin refs/heads/main` (tanpa melakukan pull/reset/checkout):

| Repository | Direktori Lokal | Remote GitHub | Branch | Local HEAD | Remote `origin/main` | Status Working Tree |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Integrasi** | `D:\KULIAH\KODINGAN\xoose-loveyou` | `https://github.com/Jeskozyx/xoose-mss-integrated.git` | `main` | `af9e083` | `af9e083` (**Sinkron**) | 2 file spesifikasi untracked (`specific_screen_xoose_loveyou.md`, `Specific Screen Xoose-LoveYou.pdf`) |
| **LoveYou** | `D:\KULIAH\KODINGAN\screenshotusingpy` | `https://github.com/Jeskozyx/loveyou-mss.git` | `main` | `6f67275` | `6f67275` (**Sinkron**) | **Clean** |
| **Xoose** | `D:\laragon\www\xoose` | `https://github.com/Jeskozyx/xoose-.git` | `main` | `cce0774` | `cce0774` (**Sinkron**) | **Clean** *(mencakup commit user terbaru `cce0774`: "last work before finale")* |

---

## 2. Audit Toolchain, Browser Lokal, & Windows Registry

### 2.1 Runtime & Tools Terpasang

| Tool / Engine | Versi Aktual | Lokasi / Catatan | Kesiapan |
| :--- | :--- | :--- | :--- |
| **Python** | `3.14.10` | `C:\Users\Jeskozyx\AppData\Local\Programs\Python\Python314\python.exe` (global, tanpa `.venv` di `screenshotusingpy` maupun `builder`) | Siap |
| **Paket Python** | `mss 10.2.0`, `Pillow 13.0.0`, `pydantic 2.14.3`, `pytest 9.2.0`, `pyinstaller 6.22.3`, `requests 2.34.2`, `supabase 2.34.1`, `pywin32-ctypes 0.2.3` | `pywin32` penuh tidak terpasang, namun API Win32 (`GetForegroundWindow`, `GetWindowThreadProcessId`, `QueryFullProcessImageNameW`) bisa memakai `ctypes` stdlib tanpa dependency baru | Siap |
| **Node.js & NPM** | Node `v26.8.1`, NPM `11.19.0` | `C:\Program Files\nodejs\` | Siap untuk unit test Extension (`Vitest`/`node:test`) & Vite build |
| **PHP & Laravel** | PHP `8.5.9` (ZTS VC2022 x64), Laravel `^13.17` (`13.43`), PHPUnit `^12.5.12` | `D:\laragon\bin\php\php-8.5.9-Win32-vs17-x64\php.exe`. `composer` tidak ada di PATH, namun `vendor/` sudah lengkap & tidak perlu package Composer baru | Siap |
| **Vite & Tailwind** | Vite `^8.0.0`, Tailwind CSS `^4.0.0` | Siap di `D:\laragon\www\xoose` | Siap |
| **Git** | `2.55.0.windows.5` | `C:\Program Files\Git\cmd\git.exe` | Siap |

### 2.2 Status Browser Terpasang & Registry Native Messaging (TEMUAN #2)

| Browser | Status Instalasi di Mesin Lokal | Path Executable | Registry Key `HKCU\...\NativeMessagingHosts` |
| :--- | :--- | :--- | :--- |
| **Google Chrome** | **TERPASANG** (`v157.0.8103.79`) | `C:\Program Files\Google\Chrome\Application\chrome.exe` | **Ada** (`com.microsoft.browsercore`, `com.tonec.idm`) |
| **Microsoft Edge** | **TIDAK TERPASANG** *(hanya ada `EdgeWebView`/`EdgeCore` runtime)* | Tidak ditemukan (`msedge.exe` tidak ada) | **Ada** (`com.tonec.idm`) |
| **Mozilla Firefox** | **TIDAK TERPASANG** | Tidak ditemukan (`firefox.exe` tidak ada) | **Ada** (`com.tonec.idm`) |

> **Dampak untuk BC-2, BC-3, BC-6, & BC-7:**  
> Kode extension, manifest host (`chrome.template.json`, `edge.template.json`, `firefox.template.json`), script registrasi HKCU (`install-host.ps1`/`uninstall-host.ps1`), serta automated tests untuk ketiga browser tetap dapat dibangun 100%. Namun untuk uji **manual/live browser E2E di BC-7**, saat ini hanya **Google Chrome** yang tersedia di mesin lokal kecuali Microsoft Edge dan Mozilla Firefox diinstal terlebih dahulu.

---

## 3. Audit Mendalam Ketiga Repository

### 3.1 Laravel Xoose (`D:\laragon\www\xoose`)

#### Komponen Eksisting yang Siap Dimanfaatkan
- **Agent API (`routes/api.php`):** Seluruh endpoint `/api/v1/agent/*` sudah tersedia dengan middleware `agent.auth` & rate limiting:
  - `GET /api/v1/agent/configs` (`ConfigApiController@index`) — sudah mendukung filter versi lokal (`versions[service_key]`) & mengembalikan konfigurasi efektif (`device override > app default`) dengan dukungan `force_apply`.
  - `POST /api/v1/agent/status` (`StatusApiController@store`) — sudah menerima `service_key`, `current_status`, `active_config_version`, dan **`details` (JSON array bebas)**. Ini **langsung siap** menampung laporan status live `BrowserCaptureService` (status extension, browser terhubung, rule aktif, mode izin, sesi lokal, jumlah capture, error terakhir, `config_version`) **tanpa mengubah skema tabel `service_status`!**
  - `POST /api/v1/agent/heartbeat` (`HeartbeatApiController@store`) — juga menyimpan ringkasan tiap service ke `service_status.details`.
  - `POST /api/v1/agent/logs` (`LogApiController@store`) — menerima batch audit log dari Agent.
- **Versioning & Rollback (`ConfigVersionService`):** Sudah mendukung `updateConfig()`, `rollbackToVersion()` (`force_apply = true` + riwayat immutable), dan `resolveEffectiveConfigsForDevice()`.
- **Otorisasi (`ManagedAppPolicy`, `AppDevicePolicy`):** Sudah memakai Laravel Gate/Policy berbasis kepemilikan (`owner_id === null || owner_id === $user->id`) dan middleware `auth` pada seluruh route `/remote/*`.
- **Database:** SQLite (`database/database.sqlite`), 10 tabel Remote Control Plane sudah termigrasi di `2026_11_23_000001_create_remote_control_plane_tables.php`. **Tidak diperlukan tabel database baru** untuk fitur Specific Screen.

#### Gap & Konflik Teknis yang Ditemukan di Xoose
1. **Validator JSON Schema di `ConfigVersionService::validateAgainstSchema()` masih datar (shallow):**
   - Baris 49–96 hanya memvalidasi tipe `integer`, `number`, `boolean`, `string`, dan cek `is_array()` untuk `object`.
   - Belum mendukung validasi rekursif untuk nested object (`capture_policy`, `browser_capture`, `window_capture`) maupun tipe `array` of objects (`rules[]`, `schemes[]`, `browsers[]`).
   - Selain itu, `updateConfig()` pada baris 131 melakukan `array_merge($currentActive?->config_json ?? [], $validated)` (shallow merge), sehingga penghapusan/pengeditan item dalam array `rules` harus di-replace secara utuh pada key tingkat atasnya.
2. **Seeding `ServiceDefinition` untuk Service Baru (`browser_capture_service`):**
   - `DeviceEnrollmentService::ensureDefaultServiceDefinitions()` hanya men-seed jika `ServiceDefinition::count() === 0`. Pada DB yang sudah berisi 7 definisi layanan, penambahan `browser_capture_service` di `ServiceDefinitionSeeder` tidak akan otomatis terinsert sebelum metode tersebut diubah agar mengecek per-`service_key` (misal `updateOrCreate` saat definisi `browser_capture_service` belum ada).
3. **Sidebar & Layout (`resources/views/components/sidebar.blade.php` & `layouts/app.blade.php`):**
   - Menu *Remote Manager* saat ini memuat 6 submenu (`Applications`, `Devices`, `Service Config`, `Commands`, `Logs & Audit`, `Releases`). Submenu baru **`Capture Rules`** (`/remote/capture-rules`) dapat ditambahkan langsung ke grup `Remote Manager` dengan gaya Blade + Tailwind CSS 4 yang konsisten.

---

### 3.2 LoveYou Client (`D:\KULIAH\KODINGAN\screenshotusingpy`)

#### Komponen Eksisting yang Siap Dimanfaatkan
- **Arsitektur Modular (`backend/services/`):**
  - `BaseService` (`base.py`): kontrak standar `start`, `stop`, `pause`, `resume`, `restart`, `get_status`, `apply_config`, plus `add_status_listener` dan `get_metadata()`.
  - `ScreenshotService` (`screenshot.py`): penangkap layar periodik berbasis MSS + Pillow (`capture_fn`), terpisah rapi dari `SyncService`.
  - `SyncService` (`sync.py`): producer-consumer upload queue (kapasitas 200, auto-retry exponential backoff saat offline, pembersihan file temporer otomatis).
  - `ServiceManager` (`manager.py`): registry service, allowlist lifecycle (`start/stop/pause/resume/restart`), serta `apply_service_config()` dengan validasi Pydantic dan **rollback otomatis** bila gagal.
- **Device Agent (`backend/agent/`):**
  - `LoveYouAgent` (`runtime.py`), `AgentApiClient` (`api_client.py`), `ConfigSyncManager` (`config_sync.py`), `DeviceIdentityStore` (`identity.py` — penyimpanan terenkripsi Windows DPAPI di `%LOCALAPPDATA%\XooseLoveYouAgent\<slug>`), `CommandExecutor` (`command_executor.py`).
  - `ConfigSyncManager::sync_once()` otomatis memanggil `service_manager.apply_service_config()` dan melaporkan status terbaru ke `/api/v1/agent/status`.
- **Win32 Active Window:** `backend/screenshot_service.py` sudah memiliki `get_active_window_title()` menggunakan `ctypes.windll.user32.GetForegroundWindow()`, yang mudah diperluas dengan nama proses (`GetWindowThreadProcessId` + `QueryFullProcessImageNameW`) menggunakan `ctypes` murni untuk mendukung mode `application_window`.

#### Gap & Konflik Teknis yang Ditemukan di LoveYou
1. **Skema Pydantic (`backend/schemas/service_schemas.py`):**
   - Baru memuat 7 model layanan (`screenshot_service`..`custom_service`). Perlu penambahan skema `browser_capture_service` (plus file `backend/schemas/browser_capture.json`) dengan `enabled: False` sebagai default.
2. **Komunikasi IPC Lokal antara `LoveYouAgent` dan `native-host/host.py` (TEMUAN ARSITEKTUR PENTING):**
   - Dalam protokol WebExtensions Native Messaging, **Browser (Chrome/Edge/Firefox)** adalah proses induk yang men-spawn `host.py` via `stdin/stdout`, sedangkan `loveyou.exe` berjalan sebagai proses Windows independen.
   - Spesifikasi melarang membuka server HTTP lokal pada semua interface (`0.0.0.0`).
   - Diperlukan mekanisme IPC lokal tanpa port jaringan — direkomendasikan **User-Scoped Shared Bridge Directory** di `%LOCALAPPDATA%\XooseLoveYouAgent\bridge\` dengan atomic file write/rename (`runtime_config.json`, `host_status_<browser>.json`, dan `spool/incoming/`).
3. **Metadata `source = "browser_tab"` pada `SyncService` & Tabel Supabase `hasil_ss`:**
   - `SyncService::process_item()` dan `SupabaseLogger::log_record()` saat ini hanya menulis kolom standar `hasil_ss` (`filename`, `image_url`, `storage_path`, `device_name`, `resolution`, `active_window`, `file_size_kb`, `status`, `notes`, `created_at`, plus opsional `user_name`).
   - Jika langsung mengirim kolom baru (`source`, `browser`, `rule_id`, `origin_domain`, `image_checksum`) ke tabel Supabase yang belum memiliki kolom tersebut, insert akan gagal (`PGRST204`).
   - Perlu pola *graceful fallback* (mencoba insert dengan metadata lengkap, dan bila kolom belum ada di Supabase, fallback menyimpan metadata terstruktur rapi pada `notes` & `active_window` serta membedakan penamaan file/prefix storage untuk `browser_tab` vs `application_window` vs `desktop_mss`).
4. **Koordinasi Live Mode (`browser_domain` / `application_window` / `desktop_mss` / `disabled`) dengan MSS:**
   - Saat ini `ServiceController.start_core_services()` otomatis menjalankan `screenshot_service.start()`.
   - Perlu koordinator mode pada `ServiceManager` / `ServiceController` agar ketika admin mengganti `capture_policy.active_source` secara live, `ScreenshotService` (MSS) dan `BrowserCaptureService` otomatis saling menyelaraskan (tidak duplikat capture, tidak merusak perilaku default lama bila `browser_capture` belum diaktifkan).
5. **PyInstaller Hidden Imports & `backend/spool/incoming/`:**
   - Saat aplikasi di-compile sebagai `onefile`/`onedir`, direktori instalasi EXE bisa bersifat *read-only* (atau diekstrak ke `_MEIPASS` temporer). Karena itu, folder `spool/incoming/` untuk produksi runtime harus dipetakan ke lokasi user-writable (`%LOCALAPPDATA%\XooseLoveYouAgent\spool\incoming\`) dengan tetap menyediakan fallback/direktori default `backend/spool/incoming/` untuk dev & unit test.

---

### 3.3 Python Build Engine (`D:\KULIAH\KODINGAN\xoose-loveyou`)

#### Komponen Eksisting
- `builder/src/xoose_builder/`: `cli.py` (`validate`, `workspace`, `build`, `sign`), `manifest.py` (sudah punya hard security guard `assert_no_forbidden_secrets`), `workspace.py` (copy terisolasi, tidak pernah mengubah source template asli), `builder.py` (PyInstaller orchestrator + secret log sanitizer), `signer.py` (SHA-256 & HMAC-SHA256).
- `builder/manifests/loveyou.json` dan `template-manifest.json` sudah sinkron memakai `source_path: "D:/KULIAH/KODINGAN/screenshotusingpy"`.

#### Gap untuk Milestone BC-6
- `builder/src/xoose_builder/builder.py` perlu diperluas agar:
  - Menambahkan hidden imports baru (`services.browser_capture`, `agent.native_bridge`, dll.) ke daftar PyInstaller LoveYou.
  - Menyediakan opsi/subcommand untuk membundel artefak **Browser Extension** (Chromium & Firefox) dan **Native Messaging Host** (`PyInstaller --onedir`), beserta template manifest & script `install-host.ps1` / `uninstall-host.ps1` tanpa menyertakan token perangkat atau kunci rahasia.

---

## 4. Hasil Uji Baseline (Sebelum Perubahan Kode)

Seluruh test eksisting pada ketiga repository dijalankan dalam mode *read-only* dan **100% LULUS**:

| Repository | Perintah Uji | Hasil Aktual |
| :--- | :--- | :--- |
| **LoveYou** (`D:\KULIAH\KODINGAN\screenshotusingpy`) | `python -m pytest -q` | **20 passed** (`20.21s`) |
| **Builder Engine** (`D:\KULIAH\KODINGAN\xoose-loveyou\builder`) | `python -m pytest -q` | **14 passed, 12 subtests passed** (`6.09s`) |
| **Laravel Xoose** (`D:\laragon\www\xoose`) | `php artisan test --compact` | **38 passed / 38 tests**, 282 assertions (`7.45s`) |

---

## 5. Matriks Kompatibilitas Browser (Audit Awal)

| Aspek Teknis | Google Chrome | Microsoft Edge | Mozilla Firefox |
| :--- | :--- | :--- | :--- |
| **Manifest Format** | Manifest V3 (`service_worker`) | Manifest V3 (`service_worker`, berbagi paket `chromium/`) | MV3 Variant (`background.scripts` / `browser_specific_settings.gecko.id`) |
| **API Namespace** | `chrome.*` (Promise di MV3, butuh adapter aman) | `chrome.*` (kompatibel Chromium MV3) | `browser.*` (native Promise) |
| **Active Tab Capture** | `chrome.tabs.captureVisibleTab(winId, opts)` (`jpeg`/`png`, konversi `webp` via OffscreenCanvas/canvas/host bila perlu) | Sama dengan Chrome (`chrome.tabs.captureVisibleTab`) | `browser.tabs.captureVisibleTab(winId, opts)` (`jpeg`/`png`, konversi `webp` di host/canvas bila format `webp` tidak didukung langsung) |
| **Batas Pesan Native Messaging** | Host → Ext: **1 MB**; Ext → Host: **4 GB** *(wajib chunking aman ≤ 256 KB)* | Sama dengan Chrome *(wajib chunking aman ≤ 256 KB)* | Host → Ext: **1 MB**; Ext → Host: **4 GB** *(wajib chunking aman ≤ 256 KB)* |
| **Registry Key (`HKCU`)** | `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.xoose.loveyou.host` | `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.xoose.loveyou.host` | `HKCU\Software\Mozilla\NativeMessagingHosts\com.xoose.loveyou.host` |
| **Otorisasi Manifest Host** | `"allowed_origins": ["chrome-extension://<ID>/"]` | `"allowed_origins": ["chrome-extension://<ID>/"]` | `"allowed_extensions": ["<GECKO_ID>"]` |
| **Status Instalasi Lokal** | **Terpasang (`v157.0.8103.79`)** | **Belum terpasang** | **Belum terpasang** |

> **Catatan Penting Format WEBP pada `tabs.captureVisibleTab()`:**  
> Standar WebExtensions `tabs.captureVisibleTab()` secara resmi hanya menerima parameter `format: "jpeg"` atau `"png"` (bukan `"webp"` secara langsung). Oleh karena itu, agar persyaratan *"format gambar utama WEBP dengan fallback format yang didukung"* terpenuhi di Chrome, Edge, dan Firefox tanpa error API, alur paling bersih dan lintas-browser adalah menangkap `png`/`jpeg` dari `captureVisibleTab()` lalu mengonversi ke `webp` di sisi Extension (`OffscreenCanvas` / `canvas.convertToBlob('image/webp')` jika tersedia) **atau** saat assembly di `native-host/image_assembler.py` memakai `Pillow` (yang sudah terpasang dan mendukung WEBP), dengan fallback otomatis ke `png` bila konversi gagal.

---

## 6. Daftar Konflik & Keputusan yang Memerlukan Persetujuan Sebelum BC-1

1. **Konflik 1 — Path Direktori (`D:\KULIAH KODINGAN` vs `D:\KULIAH\KODINGAN`):**  
   Gunakan path aktual `D:\KULIAH\KODINGAN\xoose-loveyou` dan `D:\KULIAH\KODINGAN\screenshotusingpy` di seluruh kode & script.
2. **Konflik 2 — Ketersediaan Browser Lokal (Edge & Firefox belum terpasang):**  
   Kode, manifest, installer registry, dan automated test tetap dibuat lengkap untuk Chrome, Edge, dan Firefox. Pada BC-7, uji browser live dijalankan di Chrome (serta Edge/Firefox bila Anda menginstalnya sebelum BC-7; jika tidak, diverifikasi lewat automated test + checklist manual).
3. **Konflik 3 — Schema `ConfigVersionService` & Tidak Menambah Tabel DB Baru:**  
   Tetap **tanpa migrasi/tabel baru**; pakai `service_key = "browser_capture_service"` pada `service_definitions` & `service_configs`, dengan memperluas validasi rekursif object/array pada `ConfigVersionService` serta auto-ensure per `service_key`.
4. **Konflik 4 — Format Metadata `browser_tab` di Supabase `hasil_ss`:**  
   Gunakan pola *graceful fallback* pada `SupabaseLogger.log_record()` (insert kolom metadata jika tersedia, otomatis fallback ke `notes` terstruktur + `active_window` + prefix nama file `browser_<browser>_...` agar tidak pernah gagal `PGRST204` di tabel Supabase saat ini).
5. **Konflik 5 — Mekanisme IPC Lokal Agent ↔ Native Host (Tanpa HTTP Server Lokal):**  
   Gunakan direktori bridge terisolasi user-scoped (`%LOCALAPPDATA%\XooseLoveYouAgent\bridge\` + `spool/incoming/`) berbasis *atomic write/rename* untuk distribusi `runtime_config.json`, pembacaan `host_status_<browser>.json`, dan transfer spool gambar.
6. **Konflik 6 — Konversi Format WEBP dari `tabs.captureVisibleTab()`:**  
   Karena WebExtensions `captureVisibleTab()` hanya mendukung parameter native `png`/`jpeg`, konversi ke `webp` dilakukan secara deterministik menggunakan `OffscreenCanvas` (bila didukung) atau `Pillow` di `image_assembler.py` dengan fallback otomatis ke `png`.
7. **Konflik 7 — Koordinasi Mode Live & Backward Compatibility MSS:**  
   Default `browser_capture.enabled = false`. Selama belum diaktifkan / mode `desktop_mss`, perilaku MSS lama 100% tidak berubah. Saat admin mengganti `active_source` secara live (`browser_domain` / `application_window` / `desktop_mss` / `disabled`), koordinator otomatis menyelaraskan `BrowserCaptureService` dan `ScreenshotService` tanpa duplikasi capture.
