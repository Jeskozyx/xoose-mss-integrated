# Integrasi Xoose–LoveYou
## Rencana arsitektur, tahapan implementasi, instalasi tools, dan prompt untuk IDE

**Tujuan dokumen:** menjadi spesifikasi kerja untuk mengintegrasikan Laravel Xoose dengan proyek LoveYou berbasis Python sehingga Xoose dapat membuat proyek aplikasi, mengatur konfigurasi dan fitur, mengedit template secara terkontrol, lalu menjalankan proses build menjadi aplikasi Windows `.exe`.

> **Penting:** dokumen ini adalah rencana implementasi dan prompt untuk IDE. Struktur kode aktual Xoose dan LoveYou belum diaudit di dalam dokumen ini. Karena itu, IDE wajib memeriksa repository yang benar-benar ada sebelum mengubah file, mempertahankan fitur lama, dan tidak mengasumsikan nama class, route, tabel, atau entry point yang belum ditemukan.

---

# 1. Lokasi dan struktur direktori

Lokasi yang sudah ditentukan:

- Laravel Xoose: `D:\laragon\www\xoose`
- Template LoveYou asli: `D:\KULIAH\KODINGAN\screenshotusingpy`
- Root integrasi: `D:\KULIAH\KODINGAN\xoose-loveyou`

Struktur target:

```text
D:\
├── laragon\
│   └── www\
│       └── xoose\                         # Laravel Xoose yang sudah ada
│
└── KULIAH\
    └── KODINGAN\
        ├── screenshotusingpy\             # Template LoveYou asli
        │
        └── xoose-loveyou\                 # Area integrasi
            ├── builder\                   # Python Build Engine
            │   ├── src\
            │   │   └── xoose_builder\
            │   ├── tests\
            │   ├── requirements.txt
            │   ├── pyproject.toml
            │   └── README.md
            ├── workspace\                 # Salinan kerja per proyek
            │   └── {project-slug}\
            ├── builds\                    # Artefak build per proyek/build
            │   └── {project-slug}\
            ├── logs\                      # Log proses build
            ├── temp\                      # File sementara
            └── docs\                      # Dokumentasi teknis tambahan
```

`workspace`, `builds`, `logs`, dan `temp` adalah folder runtime. Folder tersebut boleh dibuat otomatis oleh aplikasi. Jangan menaruh file hasil build di folder template asli.

## 1.1 Prinsip pemisahan

1. Xoose tetap berada di `D:\laragon\www\xoose`.
2. LoveYou tetap menjadi template sumber di `D:\KULIAH\KODINGAN\screenshotusingpy`.
3. Python Build Engine berada di `D:\KULIAH\KODINGAN\xoose-loveyou\builder`.
4. Setiap proyek mempunyai workspace terpisah.
5. Hasil build, log, dan file sementara dipisahkan.
6. Build tidak boleh mengubah template sumber.
7. Setiap build harus memakai workspace yang terisolasi dan dapat dibuat ulang.

---

# 2. Target kemampuan aplikasi

Dari dashboard Xoose, pengguna yang berwenang nantinya dapat:

1. Melihat template LoveYou yang tersedia.
2. Membuat proyek aplikasi baru berdasarkan template.
3. Mengisi identitas aplikasi dan konfigurasi.
4. Mengaktifkan atau menonaktifkan fitur yang memang disediakan template.
5. Mengubah bagian template yang diizinkan, termasuk UI/source yang relevan, dengan validasi dan pencatatan revisi.
6. Melihat preview atau melakukan pengujian sebelum build jika mekanisme preview tersedia.
7. Menjalankan build Windows.
8. Melihat status, log, waktu, dan pesan kesalahan build.
9. Mengunduh artefak hasil build.
10. Membuat build ulang tanpa mengubah proyek lain.

**Batasan penting:** jangan membuat editor source code yang mengeksekusi kode sembarang dari browser/server. Untuk tahap awal, sediakan editor file terbatas dengan daftar file yang diizinkan, validasi path, backup/revision, dan larangan mengedit file sensitif. Fitur edit bebas dapat dipertimbangkan setelah sandbox dan kontrol akses matang.

---

# 3. Arsitektur dan alur aplikasi

## 3.1 Komponen

| Komponen | Lokasi | Tanggung jawab |
|---|---|---|
| Xoose (Laravel) | `D:\laragon\www\xoose` | Dashboard, autentikasi, database metadata, API internal, validasi, antrean job |
| LoveYou template | `D:\KULIAH\KODINGAN\screenshotusingpy` | Source template asli |
| Python Build Engine | `...\xoose-loveyou\builder` | Membuat workspace, menerapkan konfigurasi, validasi, menjalankan PyInstaller |
| Workspace | `...\xoose-loveyou\workspace` | Source kerja terpisah untuk setiap proyek |
| Build output | `...\xoose-loveyou\builds` | File EXE/folder distribusi hasil build |
| Logs | `...\xoose-loveyou\logs` | Log build dan diagnostik |

## 3.2 Flow utama

```text
Pengguna
   |
   v
Dashboard Xoose (Laravel)
   |
   +--> Pilih template LoveYou
   |
   +--> Buat proyek + isi konfigurasi
   |
   +--> Simpan metadata/revisi di database Xoose
   |
   v
Laravel Service / Build Job
   |
   +--> Validasi hak akses, input, path, dan status proyek
   |
   +--> Panggil Python Build Engine dengan argumen terpisah
   |
   v
Python Build Engine
   |
   +--> Validasi manifest dan versi template
   +--> Buat workspace bersih dari template sumber
   +--> Terapkan konfigurasi dan fitur
   +--> Jalankan pemeriksaan sebelum build
   +--> Jalankan PyInstaller
   +--> Simpan output, log, dan metadata
   |
   v
Laravel menerima hasil
   |
   +--> Update status build
   +--> Tampilkan log/status
   +--> Sediakan unduhan bagi pengguna berwenang
```

## 3.3 Status yang disarankan

Status proyek:
- `draft`
- `ready`
- `building`
- `built`
- `failed`
- `archived`

Status build:
- `queued`
- `preparing`
- `building`
- `succeeded`
- `failed`
- `cancelled`

Jangan menganggap build berhasil hanya karena proses Python berhasil dipanggil. Tandai `succeeded` hanya jika exit code sukses, artefak yang diharapkan benar-benar ada, dan metadata build berhasil ditulis.

---

# 4. Desain integrasi Laravel

IDE harus menyesuaikan desain ini dengan konvensi dan versi Laravel yang ditemukan pada repository. Jangan menimpa struktur yang sudah ada.

## 4.1 Konfigurasi path

Buat konfigurasi khusus, misalnya `config/application-builder.php`:

```php
<?php

return [
    'paths' => [
        'template' => env(
            'APP_BUILDER_TEMPLATE_PATH',
            'D:/KULIAH/KODINGAN/screenshotusingpy'
        ),
        'engine' => env(
            'APP_BUILDER_ENGINE_PATH',
            'D:/KULIAH/KODINGAN/xoose-loveyou/builder'
        ),
        'workspace' => env(
            'APP_BUILDER_WORKSPACE_PATH',
            'D:/KULIAH/KODINGAN/xoose-loveyou/workspace'
        ),
        'builds' => env(
            'APP_BUILDER_OUTPUT_PATH',
            'D:/KULIAH/KODINGAN/xoose-loveyou/builds'
        ),
        'logs' => env(
            'APP_BUILDER_LOG_PATH',
            'D:/KULIAH/KODINGAN/xoose-loveyou/logs'
        ),
        'temp' => env(
            'APP_BUILDER_TEMP_PATH',
            'D:/KULIAH/KODINGAN/xoose-loveyou/temp'
        ),
    ],

    'python' => env('APP_BUILDER_PYTHON', 'python'),
    'build_timeout' => (int) env('APP_BUILDER_TIMEOUT', 3600),
];
```

Tambahkan ke `.env` lokal Xoose:

```dotenv
APP_BUILDER_TEMPLATE_PATH="D:/KULIAH/KODINGAN/screenshotusingpy"
APP_BUILDER_ENGINE_PATH="D:/KULIAH/KODINGAN/xoose-loveyou/builder"
APP_BUILDER_WORKSPACE_PATH="D:/KULIAH/KODINGAN/xoose-loveyou/workspace"
APP_BUILDER_OUTPUT_PATH="D:/KULIAH/KODINGAN/xoose-loveyou/builds"
APP_BUILDER_LOG_PATH="D:/KULIAH/KODINGAN/xoose-loveyou/logs"
APP_BUILDER_TEMP_PATH="D:/KULIAH/KODINGAN/xoose-loveyou/temp"
APP_BUILDER_PYTHON="python"
APP_BUILDER_TIMEOUT=3600
```

Jangan commit `.env`. Jangan memasukkan secret atau credential ke manifest, log, atau EXE.

## 4.2 Paket Laravel

Periksa `composer.json` terlebih dahulu. Laravel biasanya sudah memakai Symfony Process sebagai dependency; verifikasi sebelum menambah paket. Jika belum tersedia, gunakan Composer untuk memasang komponen Process yang kompatibel dengan versi dependency proyek:

```bash
composer show symfony/process
```

Jika belum terpasang dan kompatibilitas sudah diperiksa:

```bash
composer require symfony/process
```

Jangan menjalankan upgrade massal dependency Laravel hanya untuk fitur builder.

## 4.3 Modul Laravel yang direncanakan

Nama berikut adalah rancangan, bukan asumsi bahwa file tersebut sudah ada. Ikuti pola penamaan repository Xoose.

- `AppTemplate` model: data template dan versi.
- `AppProject` model: proyek hasil konfigurasi.
- `AppRevision` model: snapshot perubahan konfigurasi/source.
- `AppBuild` model: setiap percobaan build.
- `ApplicationBuilderController`: halaman/API daftar template dan proyek.
- `AppProjectController`: membuat, melihat, mengubah, dan mengarsipkan proyek.
- `AppBuildController`: meminta build, melihat status/log, dan mengunduh artefak.
- `WorkspaceService`: komunikasi Laravel dengan Python engine.
- `BuildService`: mengelola lifecycle build dan hasilnya.
- `BuildApplicationJob`: menjalankan build secara asynchronous jika queue sudah tersedia.

Rute harus memakai middleware autentikasi dan authorization/policy yang sesuai dengan sistem Xoose. Jangan membuka endpoint build atau unduhan untuk pengunjung anonim.

## 4.4 Database metadata

Rancangan tabel minimum:

**`app_templates`**
- `id`
- `name`
- `slug` (unique)
- `version`
- `source_path`
- `manifest_path` atau informasi manifest
- `is_active`
- timestamps

**`app_projects`**
- `id`
- `app_template_id` (foreign key)
- `name`
- `slug` (unique)
- `status`
- `configuration` (JSON)
- `workspace_path`
- `created_by` jika sistem Xoose memiliki user
- timestamps

**`app_revisions`**
- `id`
- `app_project_id`
- `revision_number`
- `configuration` (JSON)
- `change_summary`
- `created_by`
- timestamps

**`app_builds`**
- `id`
- `app_project_id`
- `revision_id` nullable
- `status`
- `engine_version`
- `started_at`
- `finished_at`
- `exit_code` nullable
- `artifact_path` nullable
- `log_path` nullable
- `error_message` nullable
- timestamps

Gunakan migration sesuai versi Laravel. Tambahkan index, foreign key, dan aturan penghapusan yang aman. Jangan menghapus artefak atau proyek lain secara cascading tanpa keputusan eksplisit.

---

# 5. Python Build Engine

## 5.1 Versi dan instalasi

Gunakan Python 3 versi stabil yang kompatibel dengan dependency LoveYou dan PyInstaller. Sebelum memilih versi, periksa `requirements.txt`, source import, dan dokumentasi proyek LoveYou. Jangan meng-upgrade dependency aplikasi tanpa alasan.

Buka PowerShell:

```powershell
cd D:\KULIAH\KODINGAN
New-Item -ItemType Directory -Force -Path .\xoose-loveyou\builder
New-Item -ItemType Directory -Force -Path .\xoose-loveyou\workspace
New-Item -ItemType Directory -Force -Path .\xoose-loveyou\builds
New-Item -ItemType Directory -Force -Path .\xoose-loveyou\logs
New-Item -ItemType Directory -Force -Path .\xoose-loveyou\temp

python --version
python -m pip --version
```

Buat virtual environment khusus engine:

```powershell
cd D:\KULIAH\KODINGAN\xoose-loveyou\builder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Jika PowerShell memblokir aktivasi, gunakan Python dari path langsung:

```powershell
.\.venv\Scripts\python.exe --version
```

Buat `requirements.txt` untuk engine. Isi final harus ditentukan setelah audit dependency LoveYou. Minimal, PyInstaller dapat ditambahkan dengan versi yang sudah diuji:

```text
pyinstaller
```

Instalasi:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m PyInstaller --version
```

Jangan menganggap `pyinstaller` saja cukup untuk aplikasi LoveYou. Dependency runtime LoveYou (misalnya GUI, browser automation, imaging, atau library lain) harus diinventarisasi dan dipasang sesuai source proyek. Jangan memasang paket tebakan.

## 5.2 Bentuk CLI engine

Rancang CLI yang dapat dipanggil Laravel secara konsisten, misalnya:

```powershell
python -m xoose_builder.cli validate --manifest "path\manifest.json"
python -m xoose_builder.cli workspace --manifest "path\manifest.json"
python -m xoose_builder.cli build --manifest "path\manifest.json"
```

Argumen aktual boleh disesuaikan, tetapi harus:
- menerima path melalui argumen terpisah, bukan shell command string gabungan;
- memvalidasi semua path dan slug;
- mengembalikan exit code non-zero saat gagal;
- mencetak hasil terstruktur JSON ke stdout;
- menulis detail diagnostik ke stderr/log;
- tidak mencetak secret;
- tidak menerima perintah shell bebas dari request web.

Contoh bentuk respons JSON:

```json
{
  "success": true,
  "project_slug": "contoh-aplikasi",
  "status": "workspace_created",
  "workspace_path": "D:/KULIAH/KODINGAN/xoose-loveyou/workspace/contoh-aplikasi"
}
```

## 5.3 Workspace

Workspace harus dibuat dari template sumber dengan aturan:
- pastikan source path adalah folder template yang terdaftar dan diizinkan;
- jangan mengikuti symlink yang keluar dari root template;
- jangan menyalin `.git`, `.venv`, `venv`, `__pycache__`, cache, `dist`, `build`, dan file sementara yang tidak diperlukan;
- jangan pernah menyalin `.env` atau credential ke paket distribusi;
- validasi slug dengan allowlist karakter sederhana;
- pastikan tujuan berada di bawah root workspace;
- jika workspace proyek sudah ada, jangan menimpanya diam-diam; gunakan strategi backup/revision atau konfirmasi eksplisit;
- buat salinan baru yang bersih untuk setiap build atau revision yang dibutuhkan.

## 5.4 Manifest template

LoveYou harus memiliki manifest yang menjelaskan identitas template, versi, entry point, opsi konfigurasi, fitur, file yang boleh diedit, dan pengaturan build.

Contoh struktur konseptual:

```json
{
  "template": {
    "id": "loveyou",
    "name": "LoveYou",
    "version": "1.0.0"
  },
  "application": {
    "name": "Nama Aplikasi",
    "slug": "nama-aplikasi",
    "version": "1.0.0"
  },
  "build": {
    "platform": "windows",
    "format": "onedir",
    "entry_point": "PATH_ENTRY_POINT_YANG_SUDAH_DIVERIFIKASI"
  },
  "features": {},
  "configuration": {},
  "editable_files": []
}
```

`PATH_ENTRY_POINT_YANG_SUDAH_DIVERIFIKASI` adalah placeholder, bukan path literal. IDE wajib menemukan entry point sebenarnya di LoveYou sebelum mengisi manifest.

Manifest menjadi kontrak antara Laravel dan Python. Laravel membaca schema/opsi manifest untuk membangun form konfigurasi secara dinamis. Validasi dilakukan di Laravel dan di Python.

---

# 6. PyInstaller dan strategi build

## 6.1 Tahap awal: `onedir`

Mulai dari mode `onedir` karena lebih mudah diperiksa dan didiagnosis. Output berupa folder distribusi yang berisi executable dan dependency.

Setelah build `onedir` stabil, baru uji mode `onefile` jika memang dibutuhkan. `onefile` tidak otomatis lebih aman dan dapat memiliki waktu startup/ekstraksi tambahan.

## 6.2 Proses build

1. Validasi proyek dan revision.
2. Buat workspace bersih.
3. Terapkan konfigurasi dan feature flags.
4. Validasi file wajib dan dependency.
5. Jalankan test/smoke test yang tersedia.
6. Jalankan PyInstaller dengan spec file atau argumen yang dikontrol.
7. Verifikasi exit code dan keberadaan executable.
8. Simpan output di folder build unik, misalnya berdasarkan project slug dan build ID.
9. Simpan log dan metadata.
10. Kembalikan status ke Laravel.

Jangan menerima `pyinstaller_args`, script path, atau command arbitrary langsung dari browser. Opsi build harus berasal dari konfigurasi yang sudah divalidasi dan daftar yang diizinkan.

## 6.3 Data sensitif dan Supabase

Kedua aplikasi menggunakan satu project Supabase, tetapi:
- jangan pernah memasukkan `service_role` key ke EXE, frontend, source yang didistribusikan, atau log;
- gunakan publishable/anon key hanya jika memang sesuai dengan arsitektur client;
- aktifkan dan uji Row Level Security (RLS) untuk seluruh tabel yang dapat diakses client;
- jangan menyimpan password/token rahasia sebagai konfigurasi aplikasi yang bisa diunduh;
- gunakan backend/server-side untuk operasi yang memerlukan hak istimewa;
- pisahkan data antar proyek/pengguna dengan kebijakan akses yang eksplisit.

---

# 7. Keamanan fitur LoveYou

LoveYou memiliki fungsi screenshot dan startup Windows. Fitur tersebut harus dirancang transparan dan berbasis persetujuan.

Persyaratan wajib:
1. Screenshot hanya berjalan setelah opt-in yang jelas dari pengguna.
2. Tampilkan indikator yang terlihat saat pengambilan screenshot berlangsung.
3. Sediakan kontrol pause/stop yang mudah ditemukan.
4. Jelaskan tujuan, waktu, lokasi penyimpanan, dan pihak yang dapat mengakses screenshot.
5. Jangan membuat screenshot diam-diam, menyembunyikan proses, menghindari deteksi, atau mengirim screenshot tanpa persetujuan.
6. Startup Windows harus opt-in, dapat dinonaktifkan, dan dijelaskan kepada pengguna.
7. Jangan menambahkan persistence tersembunyi.
8. Jangan mengumpulkan data di luar fungsi yang dijelaskan.
9. Log tidak boleh berisi token, password, atau konten sensitif.

---

# 8. Tahapan implementasi dan acceptance criteria

Kerjakan berurutan. Jangan mengerjakan seluruh sistem sekaligus tanpa menguji setiap milestone.

## Milestone 0 — Audit dan baseline

- Buka Xoose dan LoveYou.
- Catat versi Laravel, PHP, Python, dependency, struktur folder, entry point, cara menjalankan aplikasi, dan cara build LoveYou saat ini.
- Identifikasi fitur Xoose yang sudah ada dan area yang aman untuk integrasi.
- Jalankan test/lint yang tersedia sebelum perubahan.
- Buat laporan audit dan daftar risiko.

**Selesai jika:** IDE dapat menjelaskan struktur aktual, entry point LoveYou yang terbukti, perintah run/build yang sudah ada, dan file Xoose yang akan disentuh.

## Milestone 1 — Folder dan konfigurasi

- Buat folder `builder`, `workspace`, `builds`, `logs`, `temp`, `docs`.
- Buat konfigurasi path Laravel.
- Buat pemeriksaan health/check path.
- Pastikan Laravel dapat membaca folder template dan engine.

**Selesai jika:** pemeriksaan path lulus dan tidak ada file template yang berubah.

## Milestone 2 — Python engine dasar

- Buat package Python, CLI, logging, validasi input, dan JSON output.
- Implementasikan `validate` dan `workspace`.
- Tambahkan unit test untuk slug, path traversal, workspace collision, dan folder tidak ditemukan.

**Selesai jika:** CLI dapat membuat workspace uji dan menolak input path berbahaya.

## Milestone 3 — Manifest dan konfigurasi

- Audit konfigurasi LoveYou.
- Buat manifest schema.
- Petakan field manifest ke form Xoose.
- Terapkan konfigurasi ke workspace dengan validasi.
- Buat revision/backup.

**Selesai jika:** satu proyek dapat memiliki konfigurasi berbeda tanpa memengaruhi proyek lain atau template asli.

## Milestone 4 — Integrasi Laravel

- Buat migration, model, service, controller, policy, dan route.
- Gunakan Symfony Process dengan array argument.
- Validasi otorisasi dan kepemilikan proyek.
- Jalankan proses panjang melalui queue jika lingkungan Xoose mendukungnya.
- Simpan status, log, dan error secara aman.

**Selesai jika:** pengguna berwenang dapat membuat proyek dan meminta workspace melalui dashboard/API.

## Milestone 5 — PyInstaller

- Identifikasi entry point dan hidden imports yang benar dari source.
- Siapkan `.spec` file yang dapat direproduksi jika diperlukan.
- Build mode `onedir`.
- Verifikasi executable dapat dijalankan di mesin uji.
- Catat dependency dan versi engine.

**Selesai jika:** build menghasilkan executable yang berjalan dan tidak merusak template sumber.

## Milestone 6 — Editor dan feature manager

- Buat daftar file yang diizinkan untuk diedit.
- Tambahkan validasi konten, ukuran file, backup, revision, dan preview.
- Buat feature toggles berdasarkan fitur nyata di LoveYou.
- Jangan izinkan edit `.env`, secret, file engine, atau file di luar workspace.
- Uji rollback revision.

**Selesai jika:** perubahan hanya memengaruhi proyek terpilih dan dapat dikembalikan.

## Milestone 7 — UX build dan distribusi

- Tampilkan status build, progress jika tersedia, log ringkas, dan error.
- Sediakan download dengan authorization.
- Pastikan path download tidak bisa dipakai untuk membaca file arbitrer.
- Buat riwayat build dan tombol build ulang.

**Selesai jika:** alur dari buat proyek hingga download dapat dilakukan dari Xoose.

## Milestone 8 — Hardening dan dokumentasi

- Uji dua proyek build bersamaan.
- Uji build gagal dan retry.
- Uji path traversal, unauthorized access, file collision, dan kebocoran secret.
- Uji opt-in screenshot dan startup.
- Dokumentasikan instalasi, konfigurasi, backup, troubleshooting, dan release.

**Selesai jika:** semua pengujian kritis lulus dan dokumentasi dapat diikuti dari mesin Windows target.

---

# 9. Perintah instalasi dan pemeriksaan

## 9.1 Laravel/Xoose

Jalankan dari:

```powershell
cd D:\laragon\www\xoose
```

Pemeriksaan:

```powershell
php --version
composer --version
php artisan --version
composer show symfony/process
```

Setelah file konfigurasi ditambahkan:

```powershell
php artisan config:clear
php artisan route:list
```

Jalankan migration hanya setelah migration ditinjau dan database dibackup:

```powershell
php artisan migrate
```

Jika queue dipakai, periksa konfigurasi queue Xoose terlebih dahulu. Jangan mengganti driver queue yang sudah digunakan tanpa memahami dampaknya.

## 9.2 Python engine

```powershell
cd D:\KULIAH\KODINGAN\xoose-loveyou\builder
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --version
```

Jika LoveYou punya requirements sendiri, audit dan pasang dependency-nya dalam lingkungan build yang terencana. Hindari mencampur dependency Laravel/PHP dengan Python.

## 9.3 Verifikasi lokasi

```powershell
Test-Path "D:\laragon\www\xoose"
Test-Path "D:\KULIAH\KODINGAN\screenshotusingpy"
Test-Path "D:\KULIAH\KODINGAN\xoose-loveyou\builder"
Test-Path "D:\KULIAH\KODINGAN\xoose-loveyou\workspace"
Test-Path "D:\KULIAH\KODINGAN\xoose-loveyou\builds"
```

---

# 10. Prompt utama untuk IDE

Salin seluruh prompt berikut ke IDE yang memiliki akses ke folder Xoose, LoveYou, dan area integrasi.

```text
Anda bertindak sebagai senior Laravel/Python engineer dan software architect. Tugas Anda adalah mengimplementasikan integrasi antara project Laravel Xoose dan project Python LoveYou secara bertahap, aman, dapat diuji, dan tanpa merusak fitur yang sudah berjalan.

LOKASI PROJECT:
- Laravel Xoose: D:\laragon\www\xoose
- LoveYou template asli: D:\KULIAH\KODINGAN\screenshotusingpy
- Root integrasi: D:\KULIAH\KODINGAN\xoose-loveyou
- Python engine: D:\KULIAH\KODINGAN\xoose-loveyou\builder
- Workspace: D:\KULIAH\KODINGAN\xoose-loveyou\workspace
- Build output: D:\KULIAH\KODINGAN\xoose-loveyou\builds
- Logs: D:\KULIAH\KODINGAN\xoose-loveyou\logs
- Temp: D:\KULIAH\KODINGAN\xoose-loveyou\temp

TUJUAN:
Xoose menjadi dashboard/control panel untuk membuat proyek aplikasi LoveYou, mengatur konfigurasi dan fitur, mengedit file template yang diizinkan, membuat workspace terpisah, menjalankan build Windows menggunakan PyInstaller, menyimpan hasil EXE, dan menampilkan status/log/unduhan.

ATURAN WAJIB:
1. Mulai dengan AUDIT, jangan langsung mengubah kode.
2. Periksa kedua repository dan catat versi Laravel, PHP, Python, dependency, struktur folder, route, controller, model, migration, frontend stack, entry point LoveYou, requirements, dan mekanisme build saat ini.
3. Jangan mengasumsikan nama file, class, route, tabel, atau entry point. Temukan dan verifikasi dari source aktual.
4. Jangan menimpa atau menghapus fitur Xoose yang sudah ada.
5. Jangan memindahkan atau menggabungkan seluruh source LoveYou ke dalam folder Laravel.
6. Template asli screenshotusingpy harus read-only selama proses build. Semua perubahan dilakukan di workspace.
7. Gunakan konfigurasi path melalui config Laravel dan .env. Jangan hardcode path di banyak file.
8. Gunakan Symfony Process dengan array argument, bukan shell command string hasil gabungan input user.
9. Jangan menerima arbitrary shell command atau arbitrary PyInstaller arguments dari browser.
10. Semua endpoint harus mengikuti autentikasi, authorization, policy, dan pola keamanan yang sudah dipakai Xoose.
11. Jangan menampilkan atau menyimpan secret ke log.
12. Jangan pernah memasukkan Supabase service_role key ke EXE, frontend, atau source distribusi. Pastikan RLS untuk akses client.
13. Fitur screenshot LoveYou wajib opt-in, indikator terlihat, dan memiliki pause/stop. Dilarang membuat screenshot diam-diam atau persistence tersembunyi. Startup Windows harus opt-in dan dapat dinonaktifkan.
14. Setiap tahap harus memiliki test dan acceptance criteria. Jangan lanjut ke milestone berikutnya jika milestone sebelumnya gagal.
15. Sebelum mengubah file, tampilkan daftar file yang akan dibuat/diubah dan alasan perubahan. Setelah perubahan, tampilkan ringkasan dan test yang dijalankan.

TAHAP KERJA:

MILESTONE 0 — AUDIT:
- Audit Xoose dan LoveYou.
- Jalankan pemeriksaan/test yang aman.
- Temukan entry point LoveYou yang benar dan cara build yang sekarang.
- Laporkan dependency Python yang benar-benar digunakan.
- Laporkan komponen Laravel yang sudah tersedia, termasuk Symfony Process dan queue.
- Buat docs/audit.md di root integrasi.
- Jangan ubah kode aplikasi pada milestone ini.

MILESTONE 1 — FOLDER DAN CONFIG:
- Buat folder builder, workspace, builds, logs, temp, docs.
- Tambahkan config/application-builder.php dengan path:
  template = D:/KULIAH/KODINGAN/screenshotusingpy
  engine = D:/KULIAH/KODINGAN/xoose-loveyou/builder
  workspace = D:/KULIAH/KODINGAN/xoose-loveyou/workspace
  builds = D:/KULIAH/KODINGAN/xoose-loveyou/builds
  logs = D:/KULIAH/KODINGAN/xoose-loveyou/logs
  temp = D:/KULIAH/KODINGAN/xoose-loveyou/temp
- Tambahkan contoh .env ke dokumentasi, jangan menimpa .env aktual dan jangan commit .env.
- Buat health/path checker.

MILESTONE 2 — PYTHON ENGINE:
- Buat package Python di builder/src/xoose_builder.
- Buat CLI yang mendukung validate, workspace, dan build.
- Gunakan argparse atau pendekatan CLI standar.
- Output stdout berupa JSON yang konsisten; error detail ke stderr/log; exit code non-zero saat gagal.
- Validasi slug, path, template root, workspace root, dan symlink/path traversal.
- Buat workspace terpisah dari template; jangan menimpa workspace yang sudah ada tanpa strategi aman.
- Abaikan .git, .venv, venv, __pycache__, *.pyc, dist, build, cache, .env dan file rahasia.
- Tambahkan unit test.

MILESTONE 3 — MANIFEST:
- Berdasarkan source LoveYou, buat manifest dan schema yang mendeskripsikan template ID/version, application metadata, entry point yang sudah diverifikasi, opsi konfigurasi, feature flags, editable_files allowlist, dan build settings.
- Jangan menebak field konfigurasi; petakan dari source.
- Xoose harus dapat membangun form konfigurasi dari schema/manifest.
- Validasi manifest di Laravel dan Python.

MILESTONE 4 — LARAVEL INTEGRATION:
- Ikuti struktur dan coding convention Xoose yang ditemukan saat audit.
- Buat migration/model untuk template, project, revision, build jika belum tersedia.
- Hindari duplikasi tabel atau fitur yang sudah ada.
- Buat service untuk memanggil Python engine.
- Buat controller, policy, request validation, dan route sesuai pola Xoose.
- Gunakan queue/job untuk build yang lama jika queue tersedia dan sesuai.
- Simpan status proyek/build, waktu, exit code, log path, artifact path, dan error yang aman.
- Pastikan semua path berada di root yang diizinkan.
- Buat halaman dashboard mengikuti UI stack yang sudah digunakan Xoose.

MILESTONE 5 — PYINSTALLER:
- Gunakan dependency yang ditemukan di LoveYou.
- Tentukan entry point dari source aktual.
- Mulai dari mode onedir.
- Gunakan spec file bila dibutuhkan untuk konfigurasi reproducible.
- Jangan memasukkan .env, secret, credential, development cache, atau service_role key.
- Verifikasi output executable benar-benar ada dan dapat dijalankan.
- Baru pertimbangkan onefile setelah onedir stabil.

MILESTONE 6 — EDITOR DAN FEATURES:
- Implementasikan hanya setelah manifest dan workspace stabil.
- Editor hanya boleh mengubah file di allowlist dalam workspace proyek.
- Terapkan validasi path, ukuran, jenis file, backup, revision, dan rollback.
- Jangan izinkan edit .env, credential, file di luar workspace, atau file engine.
- Feature manager hanya menampilkan fitur yang benar-benar ditemukan dan dapat dikendalikan pada LoveYou.

MILESTONE 7 — BUILD UI:
- Tampilkan status queued/preparing/building/succeeded/failed.
- Tampilkan progress hanya jika ada data progress yang nyata; jangan mengarang persentase.
- Tampilkan log ringkas yang sudah disanitasi.
- Sediakan download hanya untuk pemilik/pengguna berwenang.
- Cegah path traversal pada download.
- Sediakan riwayat build dan build ulang.

MILESTONE 8 — TEST DAN DOKUMENTASI:
- Uji dua proyek dengan konfigurasi berbeda.
- Uji build bersamaan atau queue.
- Uji kegagalan proses dan retry.
- Uji workspace collision dan path traversal.
- Uji unauthorized access dan download.
- Uji tidak ada secret di artefak/log.
- Uji opt-in screenshot, indikator, pause/stop, dan startup toggle.
- Dokumentasikan instalasi, menjalankan engine, build, troubleshooting, backup, dan pemulihan.

OUTPUT YANG HARUS DIBERIKAN:
1. Audit struktur aktual kedua project.
2. Diagram/alur integrasi.
3. Daftar file yang dibuat/diubah.
4. Kode implementasi yang sesuai dengan versi dependency aktual.
5. Perintah instalasi dan menjalankan setiap komponen.
6. Test otomatis dan hasilnya.
7. Panduan menjalankan alur dari dashboard sampai EXE.
8. Daftar hal yang belum dapat diselesaikan dan alasannya.

CARA BEKERJA:
- Kerjakan satu milestone per sesi.
- Setelah milestone selesai, berhenti dan laporkan perubahan, command, test, hasil, dan langkah manual yang diperlukan.
- Jangan mengklaim berhasil jika test atau executable belum benar-benar dijalankan.
- Jika membutuhkan keputusan arsitektur atau ada risiko mengubah fitur lama, berhenti dan ajukan satu pertanyaan yang paling penting.
- Prioritaskan kompatibilitas dengan source aktual daripada mengikuti contoh generik secara membabi buta.
```

---

# 11. Prompt lanjutan per milestone

Jika IDE tidak dapat menyelesaikan semuanya dalam satu sesi, gunakan prompt berikut secara berurutan.

## Prompt A — Audit saja

```text
Kerjakan Milestone 0 saja. Audit Xoose dan LoveYou tanpa mengubah source aplikasi. Temukan versi framework, dependency, struktur, route, controller, database, entry point LoveYou, cara menjalankan, dan cara build. Buat docs/audit.md. Laporkan file penting dan risiko integrasi. Berhenti setelah audit.
```

## Prompt B — Fondasi folder dan Python engine

```text
Berdasarkan hasil audit yang sudah disetujui, kerjakan Milestone 1 dan 2. Buat struktur folder, config path Laravel, Python package, CLI validate/workspace, logging, JSON output, dan unit test. Jangan implementasikan PyInstaller build dulu. Uji bahwa workspace dibuat dari template tanpa mengubah template asli. Laporkan semua file dan hasil test.
```

## Prompt C — Manifest dan konfigurasi

```text
Kerjakan Milestone 3 berdasarkan source LoveYou yang telah diaudit. Buat manifest/schema berdasarkan opsi nyata di source, validasi di Python, dan integrasi pembacaan schema di Laravel. Jangan menambahkan konfigurasi atau feature flag yang tidak didukung source. Uji dua konfigurasi proyek yang berbeda.
```

## Prompt D — Laravel dashboard dan build integration

```text
Kerjakan Milestone 4 dan 5 setelah fondasi dan manifest lulus. Integrasikan model, migration, service, job, controller, policy, route, dashboard, dan PyInstaller sesuai konvensi Xoose. Mulai dari onedir. Jangan mengubah template asli. Uji end-to-end dan verifikasi executable yang dihasilkan.
```

## Prompt E — Editor, fitur, dan distribusi

```text
Kerjakan Milestone 6 sampai 8. Buat editor terbatas berbasis allowlist, revision/rollback, feature manager berdasarkan fitur nyata, build history, log, dan download terotorisasi. Jalankan pengujian keamanan dan dokumentasikan seluruh alur. Jangan menambahkan perilaku screenshot tersembunyi atau startup tanpa opt-in.
```

---

# 12. Checklist sebelum mulai

- [ ] Folder Xoose benar: `D:\laragon\www\xoose`
- [ ] Folder LoveYou benar: `D:\KULIAH\KODINGAN\screenshotusingpy`
- [ ] Root integrasi benar: `D:\KULIAH\KODINGAN\xoose-loveyou`
- [ ] IDE memiliki akses ke ketiga lokasi tersebut.
- [ ] Backup Xoose dan LoveYou sudah dibuat.
- [ ] File `.env` dan credential tidak disertakan ke prompt, repository, atau arsip.
- [ ] Versi PHP, Composer, Laravel, Python sudah diperiksa.
- [ ] Entry point LoveYou sudah ditemukan dari source.
- [ ] Build awal LoveYou masih dapat dijalankan sebelum integrasi.
- [ ] Milestone dikerjakan satu per satu dan diuji.

**Rekomendasi:** mulai dengan Prompt A (Audit saja). Jangan meminta IDE langsung membuat seluruh sistem sebelum memahami struktur aktual kedua project. Ini mengurangi risiko merusak Xoose atau menghasilkan build LoveYou yang tidak kompatibel.
