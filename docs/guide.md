# Panduan Lengkap Integrasi Xoose–LoveYou
**Versi Sistem:** 1.0.0  
**Tanggal Rilis:** 22 November 2026  
**Status Implementasi:** Milestone 0 s.d. Milestone 8 Selesai (100% Berhasil)

---

## 1. Ikhtisar Arsitektur

Integrasi ini menghubungkan aplikasi web **Laravel Xoose** dengan template Python **LoveYou** untuk menghasilkan aplikasi desktop Windows executable (`.exe`) yang mandiri dan terisolasi.

```text
Pengguna / Admin
      │
      ▼
┌────────────────────────────────────────────────────────┐
│              Dashboard Xoose (Laravel 13)              │
│  - Katalog Template & Pembuat Proyek Baru             │
│  - Validasi Input Dinamis & Form Schema                │
│  - Manajemen Revisi & Riwayat Konfigurasi              │
│  - Editor Terbatas (Allowlist) dengan Auto-Backup      │
│  - Real-time Log Monitor & Download Aman .exe / .zip   │
└──────────────────────────┬─────────────────────────────┘
                           │ Symfony Process (Array Args)
                           ▼
┌────────────────────────────────────────────────────────┐
│            Python Build Engine (xoose_builder)          │
│  - CLI: validate, workspace, build                     │
│  - Isolasi Workspace (Penyaringan File Sampah/Sensitif)│
│  - Injeksi Konfigurasi config.ini & Teks Undangan      │
│  - Sanitasi Log (Redaksi Secret & API Key)             │
│  - Orkestrasi PyInstaller (Mode onedir / onefile)      │
└────────────┬─────────────────────────────┬─────────────┘
             │ Salin Bersih                │ Kompilasi
             ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   Template Sumber Asli   │  │   Workspace & Builds     │
│   (screenshotusingpy)    │  │   (xoose-loveyou)        │
│   * Bersifat Read-Only * │  │   * Artefak .exe & Log * │
└──────────────────────────┘  └──────────────────────────┘
```

---

## 2. Struktur Direktori

```text
D:\
├── laragon\www\xoose\                         # Panel Kontrol Laravel
│   ├── app\
│   │   ├── Console\Commands\CheckBuilderPathsCommand.php
│   │   ├── Http\Controllers\
│   │   │   ├── AppProjectController.php       # CRUD Proyek
│   │   │   ├── AppBuildController.php         # Build & Download
│   │   │   └── AppEditorController.php        # Editor File Allowlist
│   │   ├── Models\ (AppTemplate, AppProject, AppRevision, AppBuild)
│   │   └── Services\
│   │       ├── TemplateManifestService.php    # Form Schema & Validasi
│   │       ├── WorkspaceService.php           # Komunikasi ke Python
│   │       └── BuildService.php               # Eksekusi PyInstaller
│   ├── config\application-builder.php         # Path & Runtime Config
│   └── resources\views\builder\               # UI Blade (index, create, show, edit, editor)
│
├── KULIAH\KODINGAN\screenshotusingpy\         # Template Asli (Read-Only)
│   ├── backend\ (screenshot_service.py, config.ini, resources\)
│   ├── frontend\src\ (index.html, invite.html, yes.html, assets\)
│   └── template-manifest.json                 # Kontrak Schema Template
│
└── KULIAH\KODINGAN\xoose-loveyou\             # Root Integrasi
    ├── builder\                               # Paket Python xoose_builder
    │   ├── src\xoose_builder\
    │   │   ├── cli.py                         # CLI Handler
    │   │   ├── manifest.py                    # Parser Manifest & Slug Validator
    │   │   ├── workspace.py                   # Isolasi Salinan Kerja
    │   │   ├── builder.py                     # Orkestrator PyInstaller
    │   │   └── exceptions.py                  # Error Handling
    │   ├── tests\                             # 11 Unit Test Python
    │   └── pyproject.toml
    ├── workspace\                             # Direktori Salinan Per Proyek
    │   └── {project-slug}\
    ├── builds\                                # Artefak Hasil Build
    │   └── {project-slug}\build_{id}\dist\
    ├── logs\                                  # Log Kompilasi Tersanitasi
    ├── temp\                                  # File Manifest Sementara
    └── docs\                                  # Dokumentasi Teknis
        ├── audit.md                           # Laporan Audit Awal
        └── guide.md                           # Panduan Penggunaan Ini
```

---

## 3. Alur Penggunaan dari Dashboard

### Langkah 1: Akses Menu App Builder
1. Buka browser ke alamat dashboard Xoose: `http://localhost:8000` atau `http://xoose.test`.
2. Klik menu **"App Builder"** pada sidebar kiri atau langsung akses route `/builder/projects`.

### Langkah 2: Buat Proyek Aplikasi Baru
1. Klik tombol **"+ Buat Proyek Baru"**.
2. Isi identitas aplikasi:
   - **Nama Aplikasi:** Nama tampilan aplikasi (misal: *LoveYou Sweetheart*).
   - **Project Slug:** Identifier unik folder dan route (misal: *loveyou-sweetheart*).
3. Atur **Feature Flags**:
   - *Windows Startup:* Pilih apakah aplikasi didaftarkan otomatis ke startup Windows (berbasis izin).
   - *System Tray Notification:* Aktifkan atau nonaktifkan pop-up balon saat capture.
   - *Simpan Salinan Lokal:* Pertahankan file capture di folder harddisk lokal.
4. Sesuaikan **Parameter Konfigurasi**:
   - Interval pengambilan screenshot (default: 3 detik).
   - Format gambar (`JPG` atau `PNG`) dan kualitas kompresi.
   - Kredensial Supabase (otomatis terisi anon/publishable key).
   - Teks jadwal tanggal undangan di `invite.html` dan waktu target countdown di `yes.html`.
5. Klik **"Simpan & Inisialisasi Workspace"**. Sistem akan membuat direktori kerja terpisah yang bersih dari template sumber.

### Langkah 3: Kustomisasi Template Terkontrol (Opsional)
1. Dari halaman detail proyek, klik **"Edit Source/Template"**.
2. Pilih file yang diizinkan untuk diedit (`config.ini`, `invite.html`, `yes.html`, atau `style.css`).
3. Lakukan modifikasi teks atau styling lalu klik **"Simpan Perubahan"**.
4. Sistem otomatis menyimpan file backup di folder `.backups/` dan mencatat nomor revisi baru.

### Langkah 4: Jalankan Kompilasi Build Windows (.exe)
1. Pada panel *Jalankan PyInstaller Build*, pilih format distribusi:
   - **Mode onedir (Direkomendasikan):** Eksekusi cepat, folder distribusi terstruktur dengan seluruh library yang dibutuhkan.
   - **Mode onefile:** Mengemas seluruh komponen ke dalam satu file `.exe` portable.
2. Klik tombol **"⚡ Mulai Kompilasi Build"**.
3. Terminal log akan menampilkan proses streaming PyInstaller secara langsung (live-stream).
4. Setelah status berubah menjadi `SUCCEEDED`, klik tombol hijau **"Unduh Executable (.exe)"** untuk mengunduh paket aplikasi siap pakai.

---

## 4. Keamanan & Kebijakan Data

1. **Immutability Template:**
   - Template di `screenshotusingpy` bersifat *read-only*. Semua penulisan dan build berjalan di dalam folder `xoose-loveyou/workspace/{slug}`.
2. **Pencegahan Path Traversal:**
   - Input slug divalidasi dengan regex ketat `^[a-z0-9]+(-[a-z0-9]+)*$`.
   - File editor memvalidasi *path containment* untuk memastikan tidak ada akses keluar dari direktori workspace proyek. File `.env`, file engine Python, dan file sistem tidak dapat diakses.
3. **Penyaringan Secret & Sanitasi Log:**
   - `service_role` key dilarang keras dimasukkan ke manifest atau didistribusikan ke file executable.
   - Log build disaring otomatis dengan regex (`sanitize_log_line`) untuk memask token rahasia sebelum disimpan ke disk.
4. **Persetujuan & Transparansi:**
   - Fitur Windows Startup dan notifikasi didesain berbasis *opt-in* yang dapat dikonfigurasi melalui formulir dashboard.

---

## 5. Ringkasan Verifikasi & Hasil Pengujian

- **PHPUnit Feature Tests (Laravel):**
  - `php artisan test` : **14 passed (36 assertions, 0 failures)**
  - Pengujian meliputi: Health check path, pembacaan manifest, validasi schema, pembuatan proyek & revisi, proteksi editor 403, dan status build.
- **Python Unit Tests (Build Engine):**
  - `python -m unittest discover -s tests -v` : **11 passed (11 assertions, 0 errors)**
  - Pengujian meliputi: Slug validation, path traversal, isolasi multi-proyek, penanganan collision, dan PyInstaller runner.
- **Hasil Build Windows:**
  - Build `onedir` sukses menghasilkan `test-project-loveyou.exe` dengan bundling resources dan frontend webview.
  - Template sumber di `screenshotusingpy` tetap bersih dan tidak mengalami perubahan apapun.
