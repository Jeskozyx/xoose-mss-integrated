# Audit Baseline: Integrasi Xoose–LoveYou
**Tanggal Audit:** 22 November 2026  
**Status Audit:** Selesai (Milestone 0)  
**Tujuan Dokumen:** Mencatat kondisi aktual lingkungan, dependensi, arsitektur kode, entry point, mekanisme build, serta potensi risiko sebelum memulai implementasi integrasi.

---

## 1. Lokasi dan Lingkungan Runtime

| Komponen | Jalur Direktori / Eksekusi | Status / Versi |
|---|---|---|
| **Root Integrasi** | `D:\KULIAH\KODINGAN\xoose-loveyou` | Ada, bersih |
| **Laravel Xoose** | `D:\laragon\www\xoose` | Ada, Git `main` clean |
| **Template LoveYou** | `D:\KULIAH\KODINGAN\screenshotusingpy` | Ada, Git `main` clean |
| **PHP Runtime** | `php` (CLI Laragon) | PHP 8.5.9 (ZTS VC 2022 x64) |
| **Composer** | `D:\laragon\bin\composer\composer.bat` | Composer 2.10.3 |
| **Laravel Framework**| `php artisan --version` | Laravel 13.43.0 |
| **Python Runtime** | `python` (Windows App / Global) | Python 3.14.10, pip 26.2.2 |

---

## 2. Audit Proyek Laravel Xoose (`D:\laragon\www\xoose`)

### 2.1 Dependensi Composer
- `laravel/framework`: `^13.17` (terpasang `v13.43.0`)
- `symfony/process`: **Sudah terpasang** (`v8.1.10`) via dependency `laravel/framework`. Siap digunakan untuk pemanggilan Python engine via array arguments secara aman.
- `laravel/tinker`: `^3.0`
- `phpunit/phpunit`: `^12.5.12`

### 2.2 Frontend Stack
- Vite 8.0.0
- Tailwind CSS 4.0.0 (`@tailwindcss/vite`)
- `@supabase/supabase-js` 2.119.2
- Template engine: Blade murni (tidak menggunakan Inertia/Vue/React/Livewire).
  - Layout: `resources/views/layouts/app.blade.php`
  - Sidebar: `resources/views/components/sidebar.blade.php`
  - Views yang sudah ada: `resources/views/dashboard.blade.php`, `resources/views/folders.blade.php`, `welcome.blade.php`.

### 2.3 Database & Queue
- Database default: SQLite (`database/database.sqlite`).
- Migrasi yang sudah berjalan:
  1. `0001_01_01_000000_create_users_table.php` (Batch 1, Ran)
  2. `0001_01_01_000001_create_cache_table.php` (Batch 1, Ran)
  3. `0001_01_01_000002_create_jobs_table.php` (Batch 1, Ran)
- Tabel `jobs` sudah siap di database. Driver antrean `database` dapat digunakan langsung untuk `BuildApplicationJob` secara asynchronous.

### 2.4 Fitur dan Controller yang Ada
- `App\Http\Controllers\DashboardController`:
  - `index()`: Mengambil daftar folder/user dari Supabase REST endpoint `user_responses`.
  - `folders(Request $request)`: Mengambil histori screenshot dari Supabase REST endpoint `hasil_ss` difilter berdasarkan nama folder/user.
  - `storeFolder(Request $request)`: Mendaftarkan folder/user baru ke `user_responses`.
- Konfigurasi Supabase Xoose disimpan di `config/services.php`:
  - URL: `https://wqjfunxfngowxwdmyzyj.supabase.co/rest/v1`
  - Key: Supabase publishable/anon key.

### 2.5 Hasil Pengujian Awal
- `php artisan test`: **LULUS** (2 tests, 2 passed, 2 assertions). Tidak ada test yang rusak sebelum integrasi dimulai.

### 2.6 Area Aman untuk Integrasi
- Menambahkan config baru `config/application-builder.php`.
- Menambahkan model & migrasi baru: `AppTemplate`, `AppProject`, `AppRevision`, `AppBuild`.
- Menambahkan service baru: `App\Services\WorkspaceService`, `App\Services\BuildService`.
- Menambahkan controller baru: `App\Http\Controllers\AppBuilderController`, `App\Http\Controllers\AppProjectController`, `App\Http\Controllers\AppBuildController`.
- Menambahkan route baru di bawah prefix `/builder` atau `/app-projects` tanpa mengganggu route `dashboard` dan `folders`.
- Menambahkan link menu di `sidebar.blade.php`.

---

## 3. Audit Proyek LoveYou (`D:\KULIAH\KODINGAN\screenshotusingpy`)

### 3.1 Struktur File Utama
```text
D:\KULIAH\KODINGAN\screenshotusingpy\
├── backend\
│   ├── screenshot_service.py   # Entry point utama aplikasi
│   ├── main.py                 # Wrapper runner sederhana
│   ├── loveyou.spec            # PyInstaller spec file
│   ├── compile.bat             # Batch script build PyInstaller yang sudah ada
│   ├── config.ini              # Konfigurasi capture, Supabase, startup, tray
│   ├── requirements.txt        # Dependensi Python
│   ├── resources\              # Icon heart.ico, chrome.ico
│   ├── setup_check.py          # Script diagnostik Supabase
│   └── view_results.py         # Viewer galeri hasil screenshot
├── frontend\
│   └── src\
│       ├── index.html          # Halaman pembuka aplikasi
│       ├── name.html           # Input nama user
│       ├── invite.html         # Pertanyaan date (Yes / No)
│       ├── yes.html            # Countdown date & pesan konfirmasi
│       └── assets\ (css, js)   # style.css, app.js
├── screenshots\                # Folder output screenshot lokal (per user)
└── loveyou.exe                 # Artefak EXE build sebelumnya (onefile)
```

### 3.2 Entry Point Terverifikasi
- **Entry point aktual:** `backend\screenshot_service.py` (dipanggil juga via `backend\main.py`).
- Menerima argumen CLI:
  - `--ui`: Hanya membuka jendela native pywebview frontend LoveYou.
  - `--silent` / `--background`: Berjalan di latar belakang tanpa pop-up jendela.
  - `--test`: Eksekusi 1 kali pengambilan screenshot pengujian lalu keluar.
  - `--no-startup`: Menonaktifkan registrasi ke Windows Startup (Registry & Shell:Startup).
  - `--no-tray`: Berjalan tanpa system tray.
  - `--interval <detik>`: Override interval capture screenshot.

### 3.3 Dependensi Python Terpasang
Seluruh dependensi yang dibutuhkan telah terpasang dan teruji di lingkungan Python 3.14.10:
- `mss` (v10.2.0): Screenshot engine cepat
- `Pillow` (v13.0.0): Image manipulation & JPEG compression
- `pystray` (v0.19.5): Native Windows system tray icon
- `supabase` (v2.34.1): Supabase Python client
- `pywebview` (v6.2.1): Edge Chromium GUI window
- `pyinstaller` (v6.22.3): Build engine ke EXE
- `pythonnet` (v3.2.1) & `clr_loader` (v0.3.1): Interop Windows Forms untuk webview

### 3.4 Mekanisme Build Saat Ini
Saat ini LoveYou dibuild menggunakan `compile.bat`:
- Menjalankan PyInstaller dengan mode `--onefile` dan `--windowed`.
- Bundling:
  - `--icon resources\heart.ico`
  - `--add-data "resources;resources"`
  - `--add-data "..\frontend\src;frontend\src"`
- Hidden imports: `webview`, `webview.platforms.winforms`, `clr`, `pystray._win32`, `mss`, `mss.windows`, `PIL`, `supabase`.
- Collect all: `webview`, `pythonnet`.

### 3.5 Konfigurasi yang Didukung (`config.ini`)
- `[SUPABASE]`: `url`, `key`, `table_name`, `bucket_name`
- `[CAPTURE]`: `interval_seconds`, `local_folder`, `keep_local_file`, `image_format`, `jpg_quality`
- `[STARTUP]`: `auto_start`, `app_name`
- `[TRAY]`: `notifications`

---

## 4. Analisis Risiko & Keputusan Arsitektur

1. **Prinsip Immutability Template Sumber:**
   - Direktori `D:\KULIAH\KODINGAN\screenshotusingpy` harus bersifat **read-only** selama proses build.
   - Semua modifikasi (perubahan `config.ini`, penggantian icon/teks) wajib dilakukan pada salinan proyek di `xoose-loveyou\workspace\{project-slug}`.

2. **Strategi Mode Build PyInstaller:**
   - Sesuai spesifikasi, build awal pada engine baru akan diprioritaskan menggunakan mode `--onedir` terlebih dahulu agar mudah diverifikasi dan didebug dependensinya.
   - Mode `--onefile` dapat diaktifkan setelah output `onedir` terbukti stabil.

3. **Keamanan & Persetujuan (Opt-In Screenshot & Startup):**
   - Dalam template asli, `screenshot_service.py` secara default mendaftarkan diri ke registry Run dan folder Startup, serta langsung mengambil screenshot setelah aplikasi berjalan.
   - Pada integrasi builder, konfigurasi `auto_start` dan capture harus dapat dikonfigurasi melalui feature toggle / manifest, dan diberi label transparan agar pengguna memiliki kontrol penuh.

4. **Keamanan Credential:**
   - Tidak boleh menyimpan `service_role` key pada manifest, source code workspace, atau file `.exe`.
   - Gunakan anon/publishable key dengan Row Level Security (RLS) aktif pada Supabase.

---

## 5. Kesimpulan Milestone 0 & Kesiapan Milestone 1
- **Audit selesai tanpa mengubah kode aplikasi.**
- Lingkungan PHP 8.5.9, Composer 2.10.3, Laravel 13.43.0, dan Python 3.14.10 dalam kondisi sehat dan kompatibel.
- Seluruh acceptance criteria Milestone 0 telah terpenuhi. Siap dilanjutkan ke Milestone 1 (Pembuatan struktur folder dan konfigurasi path Laravel).
