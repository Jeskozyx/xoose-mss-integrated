# Milestone 0 — Repository Audit: Xoose–LoveYou Centralized Remote Service Manager

**Tanggal Audit:** 23 November 2026  
**Status:** Selesai (Milestone 0 — Read-Only Audit, Tanpa Modifikasi Kode Aplikasi)  
**Dokumen Referensi:** [integrasi_kendali_xoose_loveyou.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/integrasi_kendali_xoose_loveyou.md) & [Integrasi_kendali Xoose-LoveYou.pdf](file:///D:/KULIAH/KODINGAN/xoose-loveyou/Integrasi_kendali%20Xoose-LoveYou.pdf)  
**Baseline Sebelumnya:** [docs/audit.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/docs/audit.md)

---

## 1. Verifikasi Direktori Lokal, Repository Git, & Environment Runtime

### 1.1 Verifikasi Path Aktual vs Dokumen Blueprint (TEMUAN KRITIS)

| Komponen | Path pada Dokumen Blueprint | Path Aktual Terverifikasi | Status Eksistensi |
| :--- | :--- | :--- | :--- |
| **Root Integrasi** | `D:\KULIAH KODINGAN\xoose-loveyou` *(spasi)* | `D:\KULIAH\KODINGAN\xoose-loveyou` *(backslash)* | Path spasi: **TIDAK ADA** (`False`); Path aktual: **ADA** (`True`) |
| **LoveYou Source** | `D:\KULIAH KODINGAN\screenshotusingpy` *(spasi)* | `D:\KULIAH\KODINGAN\screenshotusingpy` *(backslash)* | Path aktual: **ADA** (`True`) |
| **Laravel Xoose** | `D:\laragon\www\xoose` | `D:\laragon\www\xoose` | **ADA** (`True`) |
| **Builder Engine** | `D:\KULIAH KODINGAN\xoose-loveyou\builder` | `D:\KULIAH\KODINGAN\xoose-loveyou\builder` | **ADA** (`True`) |
| **Workspace** | `D:\KULIAH KODINGAN\xoose-loveyou\workspace` | `D:\KULIAH\KODINGAN\xoose-loveyou\workspace` | **ADA** (`True`) — berisi 13 folder workspace proyek |
| **Build Output** | `D:\KULIAH KODINGAN\xoose-loveyou\builds` | `D:\KULIAH\KODINGAN\xoose-loveyou\builds` | **ADA** (`True`) |
| **Logs** | `D:\KULIAH KODINGAN\xoose-loveyou\logs` | `D:\KULIAH\KODINGAN\xoose-loveyou\logs` | **ADA** (`True`) |
| **Docs** | `D:\KULIAH KODINGAN\xoose-loveyou\docs` | `D:\KULIAH\KODINGAN\xoose-loveyou\docs` | **ADA** (`True`) — berisi `audit.md`, `guide.md` |
| **Temp / Templates** | `templates\` *(disebut di blueprint)* | `temp\` *(tidak ada `templates\`)* | Folder `temp/` ada; folder `templates/` belum ada |

> **Catatan Kritis:** Seluruh konfigurasi aktif di Laravel (`config/application-builder.php`) dan manifest (`template-manifest.json`, `builder/manifests/loveyou.json`) sudah menggunakan path aktual `D:\KULIAH\KODINGAN\...`. Seluruh milestone berikutnya wajib menggunakan `D:\KULIAH\KODINGAN\xoose-loveyou` dan `D:\KULIAH\KODINGAN\screenshotusingpy`.

### 1.2 Status Git Ketiga Repository

| Direktori Lokal | Remote GitHub | Branch | HEAD Commit | Working Tree |
| :--- | :--- | :--- | :--- | :--- |
| `D:\KULIAH\KODINGAN\xoose-loveyou` | `https://github.com/Jeskozyx/xoose-mss-integrated.git` | `main` | `5dcd97f` (`feat: implement CLI and workspace manager for Xoose builder engine`) | Bersih kecuali 2 file blueprint untracked (`integrasi_kendali_xoose_loveyou.md`, `Integrasi_kendali Xoose-LoveYou.pdf`) |
| `D:\KULIAH\KODINGAN\screenshotusingpy` | `https://github.com/Jeskozyx/loveyou-mss.git` | `main` | `637a214` (`feat: implement LoveYou screenshot service with Supabase integration and frontend UI`) | **Clean** |
| `D:\laragon\www\xoose` | `https://github.com/Jeskozyx/xoose-.git` | `main` | `100fa36` (`feat: add application builder create and edit views`) | **Clean** |

### 1.3 Runtime, Tools, & Dependensi Terverifikasi

| Runtime / Tool | Versi / Status Aktual | Catatan |
| :--- | :--- | :--- |
| **PHP** | `8.5.9` (ZTS VC 2022 x64) | Sesuai blueprint |
| **Laravel Framework** | `13.43.0` (`composer.json`: `^13.17`) | Sesuai blueprint |
| **Symfony Process** | `8.1.10` (terpasang via `laravel/framework`) | Sudah dipakai di `BuildService`, `WorkspaceService`, `CheckBuilderPathsCommand` |
| **PHPUnit** | `^12.5.12` | 24/24 tests passing |
| **Node.js / NPM** | Node `v26.8.1`, NPM `11.19.0` | Vite `^8.0.0`, Tailwind CSS `^4.0.0`, `@supabase/supabase-js` `^2.119.2` |
| **Python Global** | `3.14.10` (`C:\Users\Jeskozyx\AppData\Local\Programs\Python\Python314\python.exe`) | Dipakai oleh `config/application-builder.php` (`python`) |
| **Virtualenv (`.venv`)** | `builder\.venv`: **TIDAK ADA**, `screenshotusingpy\.venv`: **TIDAK ADA** | Saat ini seluruh dependensi terpasang di Python global |
| **Paket Python Terpasang** | `mss` (10.2.0), `Pillow` (13.0.0), `pystray`, `pywebview`, `supabase` (2.34.1), `httpx` (0.28.1), `requests` (2.34.2), `pydantic` (2.14.3), `PyInstaller` (6.22.3), `pythonnet`, `clr_loader`, `xoose_builder` (0.1.0) | `xoose_builder` sudah terinstal editable/lokal |
| **`pytest`** | **BELUM TERPASANG** (`ModuleNotFoundError`) | Perlu diinstal sebelum menjalankan `pytest` di Milestone 1–2 |

### 1.4 Hasil Pengujian & Diagnostik Baseline (Aktual)
- `php artisan builder:check`: **LULUS** (`[BERHASIL] Seluruh path dan environment Application Builder lulus pemeriksaan!`).
- `php artisan test` (`D:\laragon\www\xoose`): **24 passed / 24 tests** (71 assertions, `6632ms`).
- `python -m unittest discover -s tests -v` (`D:\KULIAH\KODINGAN\xoose-loveyou\builder`): **11 passed / 11 tests** (`0.533s`).

---

## 2. Audit Mendalam: LoveYou Client (`D:\KULIAH\KODINGAN\screenshotusingpy`)

### 2.1 Struktur Aktual
```text
D:\KULIAH\KODINGAN\screenshotusingpy\
├── backend\
│   ├── screenshot_service.py   # Monolitik (~1.572 baris, ~70,9 KB) — entry point utama
│   ├── main.py                 # Wrapper 7 baris -> from screenshot_service import main
│   ├── config.ini              # Konfigurasi INI ([SUPABASE], [CAPTURE], [STARTUP], [TRAY], [SECURITY], [CONTENT])
│   ├── view_results.py         # Generator/viewer galeri HTML lokal hasil SS
│   ├── setup_check.py          # Script diagnostik koneksi Supabase
│   ├── loveyou.spec / compile.bat / run_debug.bat / run_service.bat / stop.bat
│   ├── requirements.txt        # Hanya 6 paket (tanpa httpx, requests, pydantic, pytest, pythonnet)
│   ├── resources\              # heart.ico, chrome.ico
│   └── *.sql                   # create_table_hasil_ss.sql, create_table_users.sql, add_user_column.sql, fix_permissions.sql
├── frontend\src\
│   ├── index.html, name.html, invite.html, yes.html
│   └── assets\{css\style.css, js\app.js}
├── template-manifest.json      # Schema fitur, konfigurasi, & editable_files
└── loveyou.exe                 # Artefak lama di root (diabaikan saat copy workspace)
```
*Belum ada folder `backend/agent/`, `backend/services/`, `backend/schemas/`, maupun `tests/`.*

### 2.2 Pemetaan Entry Point & Lifecycle Saat Ini (`backend/screenshot_service.py`)

Seluruh tanggung jawab saat ini tergabung dalam satu file monolitik `backend/screenshot_service.py`:

| Komponen / Tanggung Jawab | Implementasi Saat Ini | Keterkaitan & Batasan |
| :--- | :--- | :--- |
| **CLI & Entry Point** | `main()` dengan argumen `--ui`, `--silent`, `--background`, `--test`, `--no-startup`, `--no-tray`, `--interval` | Single-instance dijaga Windows Mutex `Local\XooseSvcMutex_<state_id>` |
| **Config Loader** | `load_config()` membaca `config.ini` (cek `base_dir` lalu `sys._MEIPASS`) + `resolve_date_settings()` | Hanya dibaca sekali saat proses start; belum mendukung runtime reload / `config_version` |
| **Persistent Local State** | `load_app_state()`, `save_app_state()`, `clear_app_state()` via Windows Registry `HKCU\Software\XooseLoveYou\<state_id>` | Menyimpan `active_user`, `onboarding_done`, `date_accepted` |
| **Windows Startup** | `register_startup()`, `unregister_startup()`, `_clear_startup_disabled_flag()` | Mendaftarkan ke `HKCU\...\Run` dan shortcut `.lnk` di `Shell:Startup` dengan argumen `--silent` |
| **Screenshot Capture** | `ServiceController.capture_worker()` (daemon thread) + `capture_screenshot()` via `mss` + `PIL` (WEBP/JPG/PNG + budget 50 KB) | Menulis ke `%TEMP%\_xoose_temp_capture` jika `keep_local_file=False` atau `local_folder` jika `True`; dikontrol flag `is_running` & `is_paused` (belum ada objek service terpisah dengan `stop()`/`restart()` independen) |
| **Supabase Sync / Upload** | `SupabaseLogger` + `ServiceController.uploader_worker()` (daemon thread) membaca `queue.Queue(maxsize=200)` | Unggah ke bucket `screenshots` + insert ke `hasil_ss`, dengan retry jaringan saat boot; belum terpisah sebagai `SyncService` dengan persistence antrean offline ke disk |
| **System Tray** | `setup_tray()` + `_start_tray_safely()` via `pystray` | Menyediakan kontrol lokal: Buka App, Capture Sekarang, Buka Galeri, Buka Supabase, Pause/Resume, Buka Config, Uninstall, Keluar |
| **UI WebView** | `run_ui_window()` + `_launch_ui_subprocess()` + `LoveYouApi` via `pywebview` (`edgechromium`) | Single UI window mutex `Local\XooseUIMutex_<state_id>`; routing otomatis `index.html` → `name.html` → `invite.html` → `yes.html` |
| **Emergency Hotkey & Uninstall** | `start_emergency_hotkey_listener()` (`RegisterHotKey`) + `uninstall_and_clean_exit()` | Memanggil `os._exit(0)` secara paksa setelah mencabut startup, membersihkan Registry/folder lokal, dan menghentikan tray |
| **Notification / Game / Custom** | Belum ada modul terpisah (`show_tray_notifications` dibaca ke `conf`, namun belum ada pemanggilan `tray.notify()` aktif) | Siap dibangun sebagai `NotificationService`, `GameService`, `CustomService` di Milestone 1 |

### 2.3 Audit Inkonsistensi Konfigurasi (`config.ini` vs `template-manifest.json` vs `screenshot_service.py` vs `workspace.py`)

| Item | `backend/config.ini` | `load_config()` default | `template-manifest.json` & `builder/manifests/loveyou.json` | Status / Dampak |
| :--- | :--- | :--- | :--- | :--- |
| **`auto_start`** | `true` | `True` | `false` *(Opt-In)* | **INKONSISTEN (Wajib diselaraskan di Milestone 1)** — jika dijalankan langsung tanpa builder, langsung mendaftar Windows Startup secara default |
| **`image_format`** | `jpg` | `webp` | `webp` | **INKONSISTEN** — default raw `config.ini` berbeda dengan manifest |
| **`jpg_quality`** | `80` | `75` | `75` | **INKONSISTEN** — default raw `config.ini` berbeda dengan manifest |
| **`tray_notifications` vs `notifications`** | `[TRAY] notifications = false` | `show_tray_notifications = False` | Feature key: `tray_notifications` (`false`) | **BUG MAPPING di `workspace.py`:** `workspace.py` mengecek `if "notifications" in feat:` padahal schema manifest memakai key `tray_notifications`! Toggle notifikasi dari UI Xoose tidak tersinkron ke `config.ini` |
| **Hardcoded Supabase Credential** | URL & publishable key tertulis di `config.ini` | Default konstanta di baris 36–37 `screenshot_service.py` | Default di `configuration_schema` | **RISIKO ARSITEKTUR:** `invite.html` (baris 202–203) juga masih menyimpan `SUPA_URL` & `SUPA_KEY` hardcoded sebagai fallback |
| **`service_role` key** | Tidak ada di client | Tidak ada di client | Dilarang secara eksplisit di deskripsi | **AMAN** — tidak ada `service_role` key yang masuk ke `.exe` atau template |
| **Build `format` default** | N/A | N/A | `onedir` (di manifest), `compile.bat` memakai `--onefile` | Perlu konsistensi dokumentasi saat Milestone 6 |

---

## 3. Audit Mendalam: Integration Root & Build Engine (`D:\KULIAH\KODINGAN\xoose-loveyou`)

### 3.1 Struktur Aktual vs Rancangan Blueprint
Rancangan blueprint (Bagian 3.1) menyebut `builder/build_engine.py`, `manifest_loader.py`, `workspace_preparer.py`, `pyinstaller_runner.py`, `signer.py`. **Struktur aktual yang sudah berjalan dan teruji (11/11 test pass)** adalah package Python berstandar `src`-layout:

```text
D:\KULIAH\KODINGAN\xoose-loveyou\builder\
├── pyproject.toml                  # Package 'xoose-builder' v0.1.0, CLI entrypoint 'xoose-builder'
├── requirements.txt                # pyinstaller, mss, Pillow, pystray, supabase, pywebview, pythonnet
├── manifests\loveyou.json          # Salinan manifest template LoveYou (identik dengan template-manifest.json)
├── src\xoose_builder\
│   ├── cli.py                      # Subcommands: validate, workspace, build (JSON stdout)
│   ├── manifest.py                 # Manifest validator, slug regex, anti path-traversal
│   ├── workspace.py                # WorkspaceManager: clean copy, config.ini injection, date resolver, HTML customization
│   ├── builder.py                  # BuildEngine: PyInstaller runner + secret log redaction
│   └── exceptions.py               # Structured exception codes
└── tests\                          # test_cli.py, test_manifest_schema.py, test_validation.py, test_workspace.py
```

### 3.2 Catatan Kesiapan Build Engine untuk Milestone 6–7
- **Sudah berfungsi:** Validasi manifest, isolasi workspace per slug, injeksi `config.ini` (termasuk `[CONTENT]`, `[TRAY]`, `[SECURITY]`), kompilasi `onedir`/`onefile` via PyInstaller dengan bundling `--add-data` untuk `resources`, `frontend/src`, dan `config.ini`, serta redaksi token pada build log.
- **Belum ada (akan ditambahkan di Milestone 6–7):**
  - Injeksi identitas proyek & kode/URL enrollment agent (tanpa kredensial perangkat bersama).
  - Modul `signer.py` / penghitung checksum SHA-256 & digital signature release package.
  - Bundling modul baru `backend/agent/`, `backend/services/`, `backend/schemas/` dan entry point baru `backend/main.py` (memastikan kompatibilitas mundur dengan `backend/screenshot_service.py`).

---

## 4. Audit Mendalam: Laravel Xoose (`D:\laragon\www\xoose`)

### 4.1 Komponen Aktual yang Sudah Ada
- **Models & Migrasi (`database/migrations/2026_11_22_000001_create_application_builder_tables.php`):**
  - `AppTemplate` (`app_templates` — 1 row aktif)
  - `AppProject` (`app_projects` — relasi ke `template`, `revisions`, `builds`; `features` & `configuration` JSON)
  - `AppRevision` (`app_revisions`)
  - `AppBuild` (`app_builds`)
  - `User` (`users` — **0 rows**)
  - Tabel standar Laravel: `jobs` (2 rows), `failed_jobs`, `job_batches`, `cache`, `sessions`.
- **Controllers (`app/Http/Controllers/`):**
  - `DashboardController`: menampilkan folder dari Supabase `user_responses` & detail screenshot dari `hasil_ss`.
  - `AppProjectController`, `AppBuildController`, `AppEditorController`: CRUD proyek builder, trigger build (`BuildApplicationJob` / sync), download artefak, editor file workspace.
  - `SupabaseResourceController`: statistik & pembersihan resource Supabase (menggunakan `SUPABASE_SERVICE_ROLE_KEY` hanya di server-side).
- **Services & Jobs:**
  - `TemplateManifestService`, `WorkspaceService`, `BuildService`, `SupabaseResourceService`.
  - `BuildApplicationJob` (Queue driver `database`, timeout 3600s).
- **Routes (`routes/web.php`):**
  - `/`, `/dashboard`, `/folders`, `POST /api/folders`, dan grup `/builder/*`.
  - **`routes/api.php` BELUM ADA** dan `bootstrap/app.php` belum mendaftarkan parameter `api:`.
- **Views (`resources/views/`):**
  - Blade murni + Tailwind CSS 4 + Vite (`layouts/app.blade.php`, `components/sidebar.blade.php`, `dashboard.blade.php`, `folders.blade.php`, `builder/{index,create,edit,show,editor}.blade.php`).
  - Sidebar saat ini memiliki menu aktif `Dashboard`, `Folders`, `App Builder`, serta beberapa menu placeholder template (`Product`, `Customers`, `Shop`, `Income`, `Promote`).
- **Database & Control Plane Saat Ini:**
  - Laravel memakai **SQLite** (`database/database.sqlite`).
  - Supabase live (`https://wqjfunxfngowxwdmyzyj.supabase.co`) saat ini **hanya memiliki 2 tabel**: `public.hasil_ss` dan `public.user_responses` (belum ada satu pun dari 10 tabel control plane baru).
  - RLS policy lama pada `hasil_ss` & `user_responses` masih menggunakan `Allow public insert/select to anon`.

---

## 5. Daftar Konflik Arsitektur & Keputusan yang Wajib Disepakati Sebelum Milestone 1+

Sesuai **Aturan Kerja Ketat #5** (*"Jika menemukan konflik arsitektur atau struktur aktual yang berbeda, berhenti dan laporkan sebelum bertindak"*), berikut **7 konflik / perbedaan struktural aktual** yang ditemukan dan rekomendasi penanganannya:

### Konflik 1 — Perbedaan Path Direktori Root
- **Temuan:** Blueprint menyebut `D:\KULIAH KODINGAN\...`, sedangkan direktori aktual adalah `D:\KULIAH\KODINGAN\...`.
- **Rekomendasi:** Kunci seluruh implementasi & variabel `.env` menggunakan path aktual `D:\KULIAH\KODINGAN\xoose-loveyou` dan `D:\KULIAH\KODINGAN\screenshotusingpy`.

### Konflik 2 — Transparansi Blueprint vs Fitur Stealth/Tooltip Kosong Sebelumnya di LoveYou
- **Temuan:**
  - Blueprint (Bagian D.5 & 7.3) mewajibkan: indikator aktif terlihat jelas saat screenshot berjalan, kontrol lokal Stop/Pause, Windows Startup bersifat opt-in, dan **tidak menyembunyikan proses/tray**.
  - Kode aktual `screenshot_service.py` saat ini memiliki: tooltip tray yang dikosongkan (`title=" "`), preset ikon **Chrome Stealth** (mengubah nama tray & header menu menjadi `Google Chrome`), serta flag CLI `--no-tray`.
- **Rekomendasi:** Pada Milestone 1, pastikan setiap service mematuhi kontrak `BaseService` (graceful stop, kontrol lokal Pause/Stop di tray, default `auto_start = false` di `config.ini` & manifest, status indikator transparan pada tray/UI), sambil tetap mempertahankan kompatibilitas fitur lama yang disetujui user. **Mohon konfirmasi apakah tooltip status aktif & indikator screenshot akan ditampilkan kembali sesuai blueprint atau tetap minimalis.**

### Konflik 3 — Relasi 10 Tabel Control Plane dengan Tabel Builder yang Sudah Ada (`app_projects` vs `managed_apps`)
- **Temuan:** Xoose sudah memiliki tabel `app_projects`, `app_templates`, `app_revisions`, `app_builds`. Blueprint mengusulkan `managed_apps` plus 9 tabel baru lainnya.
- **Rekomendasi:** Agar tidak terjadi duplikasi data aplikasi antara `/builder/projects` dan `/remote/apps`, `managed_apps` sebaiknya memiliki relasi opsional `app_project_id` (foreign key ke `app_projects`) — atau disinkronkan otomatis saat proyek dibuat di App Builder — sehingga `AppProject` lama tidak rusak dan fitur remote tetap bersih di namespace `Remote\`.

### Konflik 4 — Lokasi Database 10 Tabel Control Plane (SQLite Laravel vs Supabase PostgreSQL)
- **Temuan:** Laravel Xoose saat ini menggunakan `DB_CONNECTION=sqlite` lokal untuk tabel builder, sedangkan komunikasi ke Supabase dilakukan melalui HTTP REST (`config/services.php` + `Http::withHeaders`), dan Supabase live baru berisi `hasil_ss` & `user_responses`.
- **Rekomendasi untuk Milestone 3:**
  - Migrasi 10 tabel control plane dibuat sebagai migrasi Laravel (sehingga `php artisan migrate` & Feature Test PHPUnit berjalan penuh di SQLite/Postgres), **DAN** disediakan script SQL DDL + RLS Policies resmi untuk Supabase PostgreSQL (serta opsi konfigurasi koneksi/sinkronisasi Supabase Control Plane & Realtime).
  - **Mohon konfirmasi** apakah Laravel Xoose akan tetap memakai database lokal (`sqlite` / PostgreSQL) sebagai backend API Agent (`/api/v1/agent/*`) dengan Supabase untuk Storage/Realtime/tabel log, atau Laravel langsung dihubungkan ke database PostgreSQL Supabase (`DB_CONNECTION=pgsql`).

### Konflik 5 — Belum Ada Autentikasi Admin & `routes/api.php` di Laravel Xoose
- **Temuan:** Belum ada login admin (`users` = 0 rows), belum ada middleware `auth` pada route web, belum ada `Policies`, dan `routes/api.php` belum terdaftar di `bootstrap/app.php`.
- **Rekomendasi:** Pada Milestone 3–4, daftarkan `routes/api.php` di `bootstrap/app.php`, bangun `AuthenticateDeviceAgent` middleware berbasis hash token perangkat (`app_devices.token_hash`), siapkan Policies kepemilikan, serta tentukan apakah dashboard `/remote/*` perlu login admin sederhana (session auth) atau dukungan seeder admin default agar tidak memblokir alur kerja Laragon lokal saat ini.

### Konflik 6 — Struktur `xoose_builder` Aktual vs Daftar File Baru Blueprint
- **Temuan:** Builder sudah berjalan baik dengan struktur `builder/src/xoose_builder/{cli.py, builder.py, workspace.py, manifest.py, exceptions.py}` (11 test lulus).
- **Rekomendasi:** Pada Milestone 6–7, **perluas** package `xoose_builder` yang ada (misalnya menambah `signer.py` dan integrasi agent injection di `workspace.py`/`builder.py`) daripada mengganti atau menduplikasi file menjadi `build_engine.py` / `workspace_preparer.py` yang berisiko merusak `BuildService.php` dan `WorkspaceService.php` yang sudah memanggil `python -m xoose_builder.cli`.

### Konflik 7 — Ketiadaan `.venv` & `pytest`, serta Konvensi Nama `.env`
- **Temuan:** `pytest` belum terpasang di Python 3.14.10; `.venv` belum dibuat; `.env` Laravel menggunakan `APP_BUILDER_*` dan `SUPABASE_KEY` (bukan `XOOSE_*` / `SUPABASE_ANON_KEY`).
- **Rekomendasi:** Instal `pytest` sebelum memulai uji Milestone 1 (dan opsional siapkan `.venv` terpisah jika user menghendaki, atau gunakan Python 3.14.10 global yang sudah memiliki seluruh paket berat seperti `pyinstaller`, `pywebview`, `pythonnet`, `supabase`). Pertahankan backward compatibility key `APP_BUILDER_*` di `config/application-builder.php`.

---

## 6. Rencana Kerja Terperinci untuk Milestone 1 (Persiapan Persetujuan)

Setelah Audit Milestone 0 ini disetujui, **Milestone 1 (Service Refactoring)** pada `D:\KULIAH\KODINGAN\screenshotusingpy` akan mencakup:
1. Membuat interface `BaseService` (`backend/services/base.py`) dan `ServiceManager` (`backend/services/manager.py`) dengan kontrak `start()`, `stop()`, `pause()`, `resume()`, `restart()`, `get_status()`, `apply_config()`, beserta metadata wajib (`service_key`, `display_name`, `supported_actions`, `current_status`, `configuration_schema`, `permission_requirements`).
2. Memecah logika monolitik `screenshot_service.py` ke 7 modul independen di `backend/services/`:
   - `screenshot.py` (`screenshot_service`)
   - `tray.py` (`tray_service`)
   - `sync.py` (`sync_service`)
   - `notification.py` (`notification_service`)
   - `ui.py` (`ui_service`)
   - `game.py` (`game_service`)
   - `custom.py` (`custom_service`)
3. Menyediakan skema validasi konfigurasi runtime di `backend/schemas/`.
4. Menyelaraskan inkonsistensi `auto_start = false` (`config.ini` vs `template-manifest.json`), `image_format = webp`, `jpg_quality = 75`, serta memperbaiki mapping `tray_notifications` (nanti di Milestone 6 / builder).
5. Mempertahankan kompatibilitas penuh dengan entry point lama `backend/screenshot_service.py` dan `backend/main.py` agar seluruh fitur sebelumnya (custom date, persistence Registry, single instance, hotkey darurat, WebP upload, UI countdown) tetap bekerja 100%.
6. Menambahkan automated unit & integration tests di `D:\KULIAH\KODINGAN\screenshotusingpy\tests\` dan menjalankannya dengan `pytest`.

---

## 7. Checklist Acceptance Criteria Milestone 0
- [x] Audit menyeluruh terhadap `D:\KULIAH\KODINGAN\xoose-loveyou`, `D:\KULIAH\KODINGAN\screenshotusingpy`, dan `D:\laragon\www\xoose` berdasarkan source code aktual.
- [x] Pemetaan entry point, arsitektur, dan lifecycle aktual screenshot/tray/startup/UI/sync terdokumentasi.
- [x] Inkonsistensi `backend/config.ini` vs `template-manifest.json` (plus bug mapping `tray_notifications` vs `notifications`) teridentifikasi dan dicatat.
- [x] Verifikasi root path (`D:\KULIAH\KODINGAN\xoose-loveyou` vs typo spasi di dokumen blueprint) dan konflik arsitektur dilaporkan.
- [x] Laporan lengkap tersimpan di `D:\KULIAH\KODINGAN\xoose-loveyou\docs\remote-service-audit.md`.
- [x] **Tidak ada satu pun file kode aplikasi yang dimodifikasi pada sesi Milestone 0 ini.**
