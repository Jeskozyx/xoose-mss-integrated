# Integrasi Xoose–LoveYou: Centralized Remote Service Manager

**Blueprint Arsitektur, Struktur Folder, Instalasi Tools/Engine, Skema Database, Route/Controller, Alur Aplikasi, Roadmap Milestone 0–7, dan Prompt IDE**

---

## Ringkasan Spesifikasi Proyek

| Parameter | Nilai Aktual |
| :--- | :--- |
| **Nama Sistem** | Xoose–LoveYou Centralized Remote Service Manager (Full Centralized Service Management) |
| **Root Integrasi (Ditetapkan)** | `D:\KULIAH KODINGAN\xoose-loveyou` *(tetap di `D:\KULIAH KODINGAN`, tidak dipindahkan ke Laragon)* |
| **Direktori Laravel Xoose** | `D:\laragon\www\xoose` |
| **Direktori Source LoveYou** | `D:\KULIAH KODINGAN\screenshotusingpy` |
| **Repository GitHub** | [xoose-mss-integrated](https://github.com/Jeskozyx/xoose-mss-integrated), [xoose-](https://github.com/Jeskozyx/xoose-), [loveyou-mss](https://github.com/Jeskozyx/loveyou-mss) |
| **Stack Utama Terverifikasi** | Laravel 13.43, PHP 8.5.9, Symfony Process 8.1.10, Blade, Tailwind CSS 4, Vite, Queue Database, Python (MSS, Pystray, PyWebView, PyInstaller), Supabase |

---

## 1. Ringkasan Eksekutif & Hasil Analisis Awal

Integrasi Xoose–LoveYou mengubah peran **Xoose** dari sekadar generator aplikasi `.exe` menjadi pusat kendali terpadu (*Full Centralized Service Management*) untuk seluruh aplikasi LoveYou dan modul pengembangan game yang sudah didistribusikan. Melalui satu dashboard, admin dapat membuat build aplikasi, mengelola perangkat terdaftar, memantau status online/offline, menyalakan/mematikan/menjeda service secara modular, mengubah konfigurasi runtime tanpa build ulang, melihat log aktivitas, serta mendistribusikan update versi terbaru.

### Kondisi Aktual Repository & Temuan Penting
- **`xoose-` (Laravel Dashboard):** Menggunakan Laravel 13.43, PHP 8.5.9, Symfony Process 8.1.10, Blade, Tailwind CSS 4, Vite, dan Queue Database.
- **`loveyou-mss` (Windows Client):** Entry point saat ini berada di `backend/screenshot_service.py` dengan komponen MSS (screenshot), Pystray (system tray), PyWebView (UI), Supabase (backend), `backend/config.ini`, `template-manifest.json`, dan build lama berbasis PyInstaller.
- **`xoose-mss-integrated`:** Fondasi Python Build Engine dan dokumentasi integrasi.
- **Temuan Inkonsistensi Wajib Diperbaiki:** `backend/config.ini` saat ini menetapkan `auto_start = true`, sedangkan `template-manifest.json` menetapkan default `auto_start = false`. Ketidaksesuaian ini wajib dicatat pada Milestone 0 dan diselaraskan pada Milestone 1.
- **Penetapan Root Integrasi:** Seluruh direktori integrasi dikunci tetap di `D:\KULIAH KODINGAN\xoose-loveyou`.

---

## 2. Arsitektur Sistem & Alur Aplikasi (Application Flow)

Sistem dipisahkan menjadi **4 lapisan terisolasi** (tidak menggabungkan kode Laravel dan Python ke dalam satu aplikasi monolitik):

```text
┌────────────────────────────────────────────────────────────────────┐
│  1. XOOSE — LARAVEL DASHBOARD (D:\laragon\www\xoose)               │
│  Application Manager · Device Manager · Service Manager            │
│  Command Center · Logs & Monitoring · Releases · Build Orchestrator│
└─────────────────────────────────┬──────────────────────────────────┘
                                  │ HTTPS API / Private Realtime
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│  2. SUPABASE CONTROL PLANE (Database, Auth/RLS, Realtime, Storage) │
│  managed_apps · app_devices · device_enrollments · service_commands│
│  service_configs · service_status · device_heartbeats · app_releases
└─────────────────────────────────┬──────────────────────────────────┘
                                  │ Outbound HTTPS Polling (+ Realtime)
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│  3. LOVEYOU AGENT — WINDOWS CLIENT                                 │
│  Device Identity · Enrollment · Command Validator & Executor       │
│  Heartbeat Reporter · Runtime Config Sync · Local Integrity Check  │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │ Internal Service Lifecycle API
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│  4. LOVEYOU MODULAR SERVICES (Service Manager)                     │
│  Screenshot Service · Tray Service · Sync Service                  │
│  Notification Service · UI Service · Game Service · Custom Service │
└────────────────────────────────────────────────────────────────────┘
```

### 2.1 Perbedaan Remote Configuration vs Remote Update

| Jenis Perubahan | Mekanisme | Perlu Build Ulang EXE? |
| :--- | :--- | :--- |
| Start / Stop / Pause / Resume / Restart Service | Remote Command (Control Plane) | Tidak |
| Mengubah interval screenshot, teks undangan, tema, preferensi | Remote Configuration (Runtime JSON) | Tidak, jika mendukung skema runtime |
| Mengubah nama aplikasi / identitas paket | Konfigurasi Build / Runtime | Tergantung implementasi |
| Mengubah source code Python, menambah fitur/service baru, update versi | Remote Update & Build Engine | Ya, melalui release package baru |

### 2.2 Alur Kerja Utama (End-to-End Flows)

1. **Alur Build & Distribusi Aplikasi:**
   Admin membuat proyek di *Application Manager* Xoose → Laravel menyalin template LoveYou ke `D:\KULIAH KODINGAN\xoose-loveyou\workspace\<project_id>` → *Queue Job* menjalankan Python Build Engine via Symfony Process → Engine menyuntikkan identitas proyek (tanpa `service_role` key dan tanpa kredensial perangkat bersama) → PyInstaller menghasilkan `.exe` di `builds/` dan log di `logs/`.
2. **Alur Device Enrollment:**
   Saat `.exe` pertama kali berjalan di Windows target, *LoveYou Agent* menghubungi endpoint `/api/v1/agent/enroll` dengan kode enrollment proyek → Backend mencatat perangkat di `app_devices` dan menerbitkan token autentikasi perangkat yang unik serta dapat dicabut (*revocable*).
3. **Alur Heartbeat & Live Monitoring:**
   Agent mengirim heartbeat berkala ke backend via koneksi keluar HTTPS (tanpa membuka port masuk di Windows) → Backend memperbarui `device_heartbeats` dan `service_status` → Dashboard menandai perangkat `Online` atau `Offline` secara akurat berdasarkan batas waktu heartbeat.
4. **Alur Eksekusi Remote Command (Contoh: STOP Service):**
   Admin menekan tombol *Stop Service* di Xoose → Backend menyimpan command berstatus `pending` lengkap dengan `command_id`, `device_id`, `expires_at`, dan identitas admin → Agent mengambil command lewat HTTPS polling (dipercepat notifikasi Supabase Realtime) → Agent memvalidasi target device, masa berlaku, daftar aksi allowlist, serta idempotency → Agent memanggil `service.stop()` secara normal → Agent mengirim acknowledgment (`succeeded`/`failed`) dan status terbaru ke Xoose.
5. **Alur Sinkronisasi Konfigurasi Runtime:**
   Admin memperbarui parameter di *Service Configuration* → Backend memvalidasi skema dan menaikkan `config_version` → Agent mendeteksi versi baru, memvalidasi skema lokal, menjalankan `apply_config()`, atau melakukan rollback otomatis jika penerapan gagal.
6. **Alur Remote Update:**
   Admin mengunggah paket release baru lengkap dengan hash SHA-256 dan tanda tangan digital di *Releases & Updates* → Agent memeriksa `app_releases`, memverifikasi integritas dan tanda tangan sebelum memasang update, lalu melakukan restart terkendali.

---

## 3. Struktur Direktori & Pemetaan Folder

### 3.1 Root Integrasi (`D:\KULIAH KODINGAN\xoose-loveyou`)

```text
D:\KULIAH KODINGAN\xoose-loveyou\
├── builder\                        # Python Build Engine & packaging scripts
│   ├── build_engine.py             # Entry point CLI untuk dipanggil Symfony Process
│   ├── manifest_loader.py          # Validasi template-manifest.json & config build
│   ├── workspace_preparer.py       # Menyalin template LoveYou + inject project metadata
│   ├── pyinstaller_runner.py       # Eksekusi PyInstaller + penamaan artefak output
│   ├── signer.py                   # Checksum SHA-256 & digital signature release
│   └── requirements.txt            # Dependensi khusus Build Engine
├── workspace\                      # Direktori kerja sementara per proyek build
│   └── <app_slug_or_uuid>\         # Salinan source LoveYou + build_config.json
├── builds\                         # Hasil kompilasi .exe dan paket release
│   └── <app_slug>\<version>\
├── logs\                           # Log proses build & diagnostik integrasi
├── docs\                           # Dokumentasi audit, arsitektur, dan SOP
│   ├── remote-service-audit.md     # Output wajib Milestone 0
│   └── integrasi_xoose-loveyou.md  # Dokumen blueprint ini
└── templates\                      # Referensi template bersih dari loveyou-mss
```

### 3.2 Struktur Modular LoveYou Client (`D:\KULIAH KODINGAN\screenshotusingpy`)

```text
D:\KULIAH KODINGAN\screenshotusingpy\
├── backend\
│   ├── main.py                     # Bootstrap baru: inisialisasi Agent & Service Manager
│   ├── screenshot_service.py       # Dipertahankan/di-refactor ke modul services/
│   ├── config.ini                  # Diselaraskan dengan template-manifest.json
│   ├── agent\
│   │   ├── identity.py             # Device ID & penyimpanan kredensial lokal
│   │   ├── enrollment.py           # Alur registrasi perangkat ke Xoose API
│   │   ├── api_client.py           # Klien HTTPS (polling, ack, heartbeat, config)
│   │   ├── realtime_listener.py    # Opsional: trigger cepat via Supabase Realtime
│   │   ├── command_executor.py     # Validasi, allowlist aksi, idempotency, eksekusi
│   │   ├── config_sync.py          # Sinkronisasi config_version & rollback
│   │   └── updater.py              # Cek release, verifikasi integritas, update
│   ├── services\
│   │   ├── base.py                 # Interface BaseService (start/stop/pause/resume/...)
│   │   ├── manager.py              # Registry & pengelola lifecycle seluruh service
│   │   ├── screenshot.py           # Screenshot Service (MSS + indikator + kontrol lokal)
│   │   ├── tray.py                 # Tray Service (Pystray)
│   │   ├── sync.py                 # Sync Service (sinkronisasi data ke backend)
│   │   ├── notification.py         # Notification Service (status & notifikasi)
│   │   ├── ui.py                   # UI Service (PyWebView)
│   │   ├── game.py                 # Game Service (fondasi modul game)
│   │   └── custom.py               # Custom Service (template ekstensi)
│   └── schemas\                    # Skema validasi konfigurasi runtime tiap service
├── tests\                          # Automated unit & integration tests (pytest)
└── template-manifest.json          # Deskripsi fitur, service default, dan opsi build
```

### 3.3 Struktur Modul Baru di Laravel Xoose (`D:\laragon\www\xoose`)

```text
D:\laragon\www\xoose\
├── app\
│   ├── Http\
│   │   ├── Controllers\
│   │   │   ├── Remote\             # Web Dashboard Controllers (8 halaman)
│   │   │   └── Api\Agent\          # API Controllers komunikasi Agent
│   │   ├── Middleware\             # AuthenticateDeviceAgent.php
│   │   └── Requests\Remote\        # Form Requests validasi command, config, release
│   ├── Jobs\                       # DispatchAppBuildJob, ExpireStaleCommandsJob, ...
│   ├── Models\                     # 10 Model Remote Management
│   ├── Policies\                   # Authorization policies per resource
│   └── Services\Remote\            # CommandDispatcher, ConfigVersioner, BuildEngine, ...
├── database\migrations\            # Migrasi 10 tabel control plane
├── resources\views\remote\         # Blade views (Tailwind CSS 4 + Vite)
├── routes\
│   ├── web.php                     # Route dashboard admin Xoose
│   └── api.php                     # Route endpoint komunikasi LoveYou Agent
└── tests\Feature\Remote\           # Feature tests endpoint & dashboard
```

---

## 4. Instalasi Framework, Tools, Engine & Dependensi

### 4.1 Daftar Komponen & Stack

| Komponen | Framework / Tools / Engine | Fungsi Utama |
| :--- | :--- | :--- |
| **Web Dashboard & API** | PHP 8.5.9, Laravel 13.43, Composer, Laragon | Control Panel terpusat, API Agent, autentikasi admin, orkestrasi build |
| **Frontend Dashboard** | Blade, Tailwind CSS 4, Vite, Node.js / NPM | Antarmuka 8 halaman manajemen tanpa framework frontend tambahan |
| **Async & Process Engine** | Laravel Queue (`database`), Symfony Process 8.1.10 | Menjalankan Python Build Engine & pemrosesan asynchronous |
| **Control Plane & Storage** | Supabase (PostgreSQL, RLS, Private Realtime, Storage) | Database control plane, notifikasi cepat, penyimpanan paket release |
| **Desktop App & Agent** | Python 3, MSS, Pystray, PyWebView, HTTPX/Requests, Pydantic | Aplikasi Windows LoveYou, modular services, komunikasi outbound Agent |
| **Build & Testing Tools** | PyInstaller, Pytest, PHPUnit / Pest, Git | Kompilasi EXE per proyek, pengujian otomatis lintas milestone |

### 4.2 Perintah Setup Environment (Windows PowerShell / CMD)

```powershell
# 1. Buat struktur direktori integrasi di D:\KULIAH KODINGAN\xoose-loveyou
mkdir "D:\KULIAH KODINGAN\xoose-loveyou\builder"
mkdir "D:\KULIAH KODINGAN\xoose-loveyou\workspace"
mkdir "D:\KULIAH KODINGAN\xoose-loveyou\builds"
mkdir "D:\KULIAH KODINGAN\xoose-loveyou\logs"
mkdir "D:\KULIAH KODINGAN\xoose-loveyou\docs"

# 2. Setup Python Virtual Environment untuk Build Engine
cd "D:\KULIAH KODINGAN\xoose-loveyou\builder"
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install pyinstaller pydantic httpx pytest

# 3. Setup Python Virtual Environment untuk LoveYou Client & Agent
cd "D:\KULIAH KODINGAN\screenshotusingpy"
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install mss pystray pywebview pillow httpx requests pydantic pytest

# 4. Setup Laravel Xoose & Queue Worker
cd "D:\laragon\www\xoose"
composer install
npm install
npm run build
php artisan migrate
php artisan queue:work database --tries=3 --timeout=300
```

### 4.3 Konfigurasi `.env` Laravel Xoose (Server-Side Only)

```dotenv
# Path Integrasi Xoose-LoveYou
XOOSE_INTEGRATION_ROOT="D:\KULIAH KODINGAN\xoose-loveyou"
XOOSE_BUILDER_PATH="D:\KULIAH KODINGAN\xoose-loveyou\builder"
XOOSE_WORKSPACE_PATH="D:\KULIAH KODINGAN\xoose-loveyou\workspace"
XOOSE_BUILDS_PATH="D:\KULIAH KODINGAN\xoose-loveyou\builds"
XOOSE_LOGS_PATH="D:\KULIAH KODINGAN\xoose-loveyou\logs"
XOOSE_PYTHON_BIN="D:\KULIAH KODINGAN\xoose-loveyou\builder\.venv\Scripts\python.exe"

# Supabase Control Plane (JANGAN PERNAH dimasukkan ke EXE)
SUPABASE_URL="[SUPABASE_PROJECT_URL]"
SUPABASE_ANON_KEY="[SUPABASE_ANON_OR_PUBLISHABLE_KEY]"
SUPABASE_SERVICE_ROLE_KEY="[SUPABASE_SERVICE_ROLE_KEY_SERVER_ONLY]"

# Parameter Remote Service Manager
DEVICE_HEARTBEAT_TIMEOUT_SECONDS=90
COMMAND_DEFAULT_TTL_SECONDS=300
```

---

## 5. Desain Database & Skema Control Plane (10 Tabel)

Seluruh tabel baru menggunakan **Row Level Security (RLS)** agar admin hanya dapat mengelola aplikasi/perangkat miliknya dan setiap Agent hanya dapat mengakses command serta konfigurasi milik perangkatnya sendiri.

| Tabel | Model Laravel | Fungsi & Kolom Kunci Utama |
| :--- | :--- | :--- |
| `managed_apps` | `ManagedApp` | Daftar aplikasi yang dibuat di Xoose (`id`, `name`, `slug`, `current_version`, `build_status`, `default_config`) |
| `app_devices` | `AppDevice` | Perangkat tempat aplikasi terpasang (`id`, `managed_app_id`, `device_code`, `hostname`, `app_version`, `status`, `token_hash`, `revoked_at`, `last_seen_at`) |
| `device_enrollments` | `DeviceEnrollment` | Proses pendaftaran perangkat (`id`, `managed_app_id`, `enrollment_code`, `status`, `expires_at`, `enrolled_device_id`) |
| `service_definitions` | `ServiceDefinition` | Katalog jenis layanan (`service_key`, `display_name`, `supported_actions`, `configuration_schema`, `permission_requirements`) |
| `service_commands` | `ServiceCommand` | Antrean instruksi remote (`command_id`, `device_id`, `service_key`, `action`, `payload`, `status`, `issued_by`, `created_at`, `expires_at`, `acknowledged_at`, `result_message`) |
| `service_configs` | `ServiceConfig` | Konfigurasi runtime berversi (`id`, `managed_app_id`, `device_id`, `service_key`, `config_version`, `config_json`, `updated_by`, `previous_version_id`) |
| `service_status` | `ServiceStatus` | Status terakhir tiap service (`device_id`, `service_key`, `current_status`, `active_config_version`, `reported_at`) |
| `device_heartbeats` | `DeviceHeartbeat` | Riwayat detak jantung koneksi perangkat (`device_id`, `app_version`, `agent_uptime`, `ip_address`, `received_at`) |
| `service_logs` | `ServiceLog` | Riwayat aktivitas, error, perubahan config, dan audit log (`device_id`, `service_key`, `level`, `event_type`, `message`, `context`, `created_at`) |
| `app_releases` | `AppRelease` | Versi aplikasi & paket update (`managed_app_id`, `version`, `artifact_path`, `sha256_checksum`, `signature`, `release_notes`, `is_active`) |

### Siklus Status Command & Struktur Payload
Alur status `service_commands`:
`pending` → `delivered` → `acknowledged` → `succeeded` / `failed` *(ditambah `expired` dan `cancelled`)*

```json
{
  "command_id": "uuid-v4",
  "device_id": "uuid-device",
  "service": "screenshot_service",
  "action": "stop",
  "payload": {},
  "status": "pending",
  "created_at": "2026-11-23T03:46:00Z",
  "expires_at": "2026-11-23T03:51:00Z"
}
```

---

## 6. Spesifikasi Route, Controller, Service, Job & Dashboard (Laravel Xoose)

### 6.1 Web Routes & Controllers (8 Halaman Dashboard — Blade + Tailwind CSS 4 + Vite)

| Halaman Dashboard | Prefix Route Web | Controller & Tanggung Jawab |
| :--- | :--- | :--- |
| **1. Application Manager** | `GET/POST /remote/apps` | `ManagedAppController` — CRUD aplikasi, trigger build EXE, status distribusi |
| **2. Device Manager** | `GET /remote/devices` | `AppDeviceController` — Daftar perangkat, filter Online/Offline, revoke akses |
| **3. Device Detail** | `GET /remote/devices/{device}` | `AppDeviceController@show` — Versi app, last seen, heartbeat, status seluruh service |
| **4. Service Manager** | `POST /remote/devices/{device}/services/{service}/command` | `ServiceControlController` — Kirim Start, Stop, Pause, Resume, Restart |
| **5. Service Configuration** | `GET/PUT /remote/configs/{scope}/{service}` | `ServiceConfigController` — Edit konfigurasi runtime, validasi skema, rollback versi |
| **6. Command History** | `GET /remote/commands` | `ServiceCommandController` — Pantau pending/succeeded/failed/expired, retry, cancel |
| **7. Logs & Monitoring** | `GET /remote/logs` | `ServiceLogController` — Filter riwayat aktivitas, error perangkat, audit log admin |
| **8. Releases & Updates** | `GET/POST /remote/releases` | `AppReleaseController` — Manajemen versi, SHA-256, tanda tangan paket, target update |

### 6.2 API Routes & Controllers (Komunikasi LoveYou Agent)

| Method & Endpoint | API Controller | Fungsi |
| :--- | :--- | :--- |
| `POST /api/v1/agent/enroll` | `EnrollmentApiController@store` | Pendaftaran perangkat baru; menerbitkan device token unik |
| `POST /api/v1/agent/heartbeat` | `HeartbeatApiController@store` | Menerima heartbeat & ringkasan status service |
| `GET /api/v1/agent/commands/pending` | `CommandApiController@pending` | HTTPS polling command aktif; menandai status `delivered` |
| `POST /api/v1/agent/commands/{command}/ack` | `CommandApiController@acknowledge` | Menerima acknowledgment & hasil eksekusi command |
| `GET /api/v1/agent/configs` | `ConfigApiController@index` | Mengambil konfigurasi runtime terbaru berdasarkan `config_version` |
| `POST /api/v1/agent/status` | `StatusApiController@store` | Pelaporan status granular tiap service |
| `POST /api/v1/agent/logs` | `LogApiController@store` | Pengiriman batch log aktivitas & error lokal |
| `GET /api/v1/agent/releases/latest` | `ReleaseApiController@latest` | Pengecekan update terbaru, checksum SHA-256, dan signature |
| `POST /api/v1/agent/unregister` | `EnrollmentApiController@revokeSelf` | Pencabutan akses perangkat secara lokal |

### 6.3 Service Layer, Queue Jobs, Policies & Form Requests
- **Services (`app/Services/Remote/`):** `CommandDispatcherService`, `ConfigVersionService`, `DeviceEnrollmentService`, `BuildEngineService` (Symfony Process), `ReleaseIntegrityService`.
- **Queue Jobs (`app/Jobs/` — Queue Database):** `DispatchAppBuildJob`, `ExpireStaleCommandsJob`, `DetectOfflineDevicesJob`, `IngestAgentLogsJob`.
- **Policies & Form Requests:** Otorisasi berbasis kepemilikan aplikasi/perangkat serta validasi payload command, skema konfigurasi, dan paket release.
- **Status UI Standar:** `Online`, `Offline`, `Pending`, `Running`, `Stopped`, `Paused`, `Failed`, `Unknown`.

---

## 7. Spesifikasi LoveYou Agent & Service Lifecycle Engine (Python)

### 7.1 Kontrak Antarmuka Lifecycle (`BaseService`)

```python
from abc import ABC, abstractmethod

class BaseService(ABC):
    service_key: str               # contoh: "screenshot_service", "game_service"
    display_name: str
    supported_actions: list[str]   # subset eksplisit dari start/stop/pause/resume/restart
    configuration_schema: dict
    permission_requirements: list[str]

    @abstractmethod
    def start(self) -> dict: ...

    @abstractmethod
    def stop(self) -> dict: ...

    @abstractmethod
    def pause(self) -> dict: ...

    @abstractmethod
    def resume(self) -> dict: ...

    @abstractmethod
    def restart(self) -> dict: ...

    @abstractmethod
    def get_status(self) -> dict: ...

    @abstractmethod
    def apply_config(self, config: dict, config_version: int) -> dict: ...
```

### 7.2 Daftar Layanan Modular

| Service Key | Teknologi / Peran | Operasi & Catatan |
| :--- | :--- | :--- |
| `screenshot_service` | MSS + Indikator Aktif | `start`, `stop`, `pause`, `resume`, `restart`, `apply_config` (wajib indikator terlihat & kontrol lokal Stop/Pause) |
| `tray_service` | Pystray | `start`, `stop`, `restart`, `get_status` (akses cepat status & kontrol lokal) |
| `sync_service` | HTTPX / Supabase | `start`, `stop`, `pause`, `resume`, `restart`, `apply_config` (sinkronisasi data & antrean offline) |
| `notification_service` | Windows Notification | `start`, `stop`, `apply_config` (notifikasi status & perubahan konfigurasi) |
| `ui_service` | PyWebView | `start`, `stop`, `restart`, `apply_config` (tema, teks, tampilan UI dinamis) |
| `game_service` | Ekstensi Game | `start`, `stop`, `pause`, `resume`, `restart`, `apply_config` (layanan khusus pengembangan game) |
| `custom_service` | Plugin Modular | Sesuai deklarasi `supported_actions` masing-masing layanan |

### 7.3 Batasan Teknis & Transparansi Wajib
1. Jangan pernah meletakkan Supabase `service_role` key atau kredensial perangkat bersama di dalam `.exe`.
2. Gunakan autentikasi perangkat unik yang dapat dicabut (*revocable*).
3. Batasi perintah pada daftar aksi terdefinisi (*allowlist*) — dilarang menyediakan *arbitrary remote shell* atau eksekusi kode arbitrer.
4. Terapkan idempotency dan validasi masa berlaku (`expires_at`) pada setiap command.
5. Pertahankan indikator aktif yang jelas, kontrol lokal Stop/Pause, dan opt-in Windows Startup untuk fitur screenshot (tidak berjalan tersembunyi).
6. Gunakan penghentian normal (*graceful stop*) untuk tiap service, bukan mematikan proses utama secara paksa.

---

## 8. Roadmap & Tahapan Implementasi (Milestone 0 – Milestone 7)

| Milestone | Fokus | Deliverables & Acceptance Criteria |
| :--- | :--- | :--- |
| **Milestone 0 — Repository Audit** | Audit kondisi aktual tanpa mengubah kode | File `docs/remote-service-audit.md`, pemetaan entry point & lifecycle saat ini, pencatatan inkonsistensi `config.ini` vs `template-manifest.json`, verifikasi root `D:\KULIAH KODINGAN\xoose-loveyou`. |
| **Milestone 1 — Service Refactoring** | Modularisasi layanan LoveYou | `BaseService`, `ServiceManager`, pemisahan 7 modul service, skema konfigurasi, penyelarasan `auto_start`, fungsi lama tetap berjalan, `pytest` lulus. |
| **Milestone 2 — LoveYou Device Agent** | Agen komunikasi Windows | Device identity, enrollment, kredensial lokal, heartbeat, HTTPS command polling (+ opsi Realtime trigger), validasi & idempotency, ack, reconnect offline, tests lulus. |
| **Milestone 3 — Control Plane & API** | Fondasi data & backend API | Migrasi 10 tabel, RLS policies, middleware device auth, API Agent lengkap, command queue & TTL expiration job, config versioning + rollback, audit logs. |
| **Milestone 4 — Laravel Dashboard** | Antarmuka pengelolaan terpusat | 8 halaman Blade + Tailwind CSS 4 + Vite, policies, form requests, feature tests lulus. |
| **Milestone 5 — End-to-End Integration** | Pengujian perangkat nyata | Uji enroll → heartbeat Online → kirim `STOP` → Agent eksekusi & ack → status `Stopped`; uji offline/reconnect, command expired, dan duplicate command. |
| **Milestone 6 — Builder Integration** | Integrasi ke Python Build Engine | Agent terpasang di template workspace `D:\KULIAH KODINGAN\xoose-loveyou\builder`, konfigurasi per proyek tanpa shared credential di EXE, uji 2 aplikasi terpisah. |
| **Milestone 7 — Update & Hardening** | Release & stabilisasi akhir | Release management, signed package, verifikasi SHA-256, rollback otomatis, revocation lokal & remote, pengujian stabilitas/keamanan, dokumentasi akhir. |

---

## 9. Prompt Utama untuk AI IDE (Siap Copy-Paste)

Salin seluruh blok prompt di bawah ini ke AI IDE Anda untuk memulai sesi **Milestone 0**:

```text
PROJECT: Xoose–LoveYou Centralized Remote Service Manager (Full Centralized Service Management)

Bertindak sebagai Senior Software Architect, Laravel Engineer, Python Engineer, dan Windows Application Engineer.
Saya ingin mengintegrasikan Xoose dan LoveYou menjadi sistem Centralized Remote Service Management untuk kebutuhan pengelolaan aplikasi dan pengembangan game saya.

A. LOKASI DIREKTORI LOKAL & REPOSITORY (WAJIB DIPATUHI)
1. Laravel Xoose:
   D:\laragon\www\xoose
2. LoveYou Source:
   D:\KULIAH KODINGAN\screenshotusingpy
3. Integration Root (TETAP DI D:\KULIAH KODINGAN, JANGAN PINDAHKAN KE LARAGON):
   D:\KULIAH KODINGAN\xoose-loveyou
4. Python Build Engine:
   D:\KULIAH KODINGAN\xoose-loveyou\builder
5. Workspace:
   D:\KULIAH KODINGAN\xoose-loveyou\workspace
6. Build Output:
   D:\KULIAH KODINGAN\xoose-loveyou\builds
7. Logs:
   D:\KULIAH KODINGAN\xoose-loveyou\logs
8. Docs:
   D:\KULIAH KODINGAN\xoose-loveyou\docs

Repository GitHub Referensi:
- https://github.com/Jeskozyx/xoose-mss-integrated
- https://github.com/Jeskozyx/xoose-
- https://github.com/Jeskozyx/loveyou-mss

Gunakan source code aktual pada direktori lokal dan ketiga repository di atas. Jangan mengandalkan README atau asumsi semata.

B. TUJUAN SISTEM
Xoose menjadi pusat kendali (Control Panel + Application Builder) untuk seluruh aplikasi LoveYou dan modul game yang dibuat serta didistribusikan.
Admin harus dapat:
- Melihat semua aplikasi yang dibuat dan memicu build EXE via Python Build Engine.
- Melihat seluruh perangkat tempat aplikasi dipasang beserta status Online/Offline dan heartbeat.
- Melihat status setiap service secara terpisah (Running, Stopped, Paused, Failed, Unknown).
- Mengirim perintah Start, Stop, Pause, Resume, dan Restart ke setiap service yang mendukungnya.
- Mengubah konfigurasi runtime (interval, teks, tema, parameter game/service) tanpa build ulang EXE.
- Melihat riwayat command (Command Center), logs aktivitas, dan error.
- Mengelola versi release aplikasi dan remote update.
- Mengatur opsi Windows Startup dan mencabut akses perangkat (revoke).

C. ARSITEKTUR 4 LAPIS (JANGAN MENGGABUNGKAN LARAVEL & PYTHON DALAM SATU PROSES)
1. Laravel Xoose (Laravel 13.43, PHP 8.5.9, Symfony Process 8.1.10, Blade, Tailwind CSS 4, Vite, Queue Database):
   Dashboard, Auth & Authorization, Application Manager, Device Manager, Service Manager, Command Center, Logs & Monitoring, Releases & Updates, Build Orchestrator, API Agent, Audit Logs.
2. Supabase Control Plane:
   Database control plane (10 tabel + RLS), device registration, command queue, configuration versioning, heartbeats, service status, service logs, private realtime notifications, release storage.
3. LoveYou Agent (Windows Client — Outbound Connection):
   Device identity, secure enrollment, HTTPS command polling (+ opsional Supabase Realtime trigger dengan verifikasi backend), command validation & idempotency, service lifecycle execution, config synchronization + rollback, heartbeat reporting, release verification.
4. LoveYou Modular Services (Service Manager):
   Screenshot Service (MSS), Tray Service (Pystray), Sync Service, Notification Service, UI Service (PyWebView), Game Service, dan Custom Service.

D. BATASAN TEKNIS & TRANSPARANSI YANG TETAP WAJIB DITERAPKAN
1. Jangan pernah menanamkan Supabase service_role key atau shared device credential ke dalam EXE.
2. Gunakan autentikasi unik per perangkat yang dapat dicabut (revocable) dari dashboard maupun secara lokal.
3. Setiap command wajib memiliki command_id, device_id, service, action, timestamp, expires_at, status, dan idempotency.
4. Batasi eksekusi command pada daftar aksi terdefinisi (allowlist supported_actions). Jangan membuat arbitrary remote shell atau eksekusi file arbitrer dari dashboard.
5. Untuk fitur Screenshot: tetap tampilkan indikator aktif yang jelas, sediakan kontrol lokal Stop/Pause, jadikan Windows Startup bersifat opt-in, jangan menyembunyikan proses/tray, dan perbaiki inkonsistensi auto_start antara backend/config.ini dan template-manifest.json.
6. Untuk Remote Update: gunakan verifikasi checksum integritas dan paket bertanda tangan digital.
7. Semua tindakan admin tercatat di audit log.

E. MODUL LARAVEL YANG DIRENCANAKAN
Ikuti coding convention aktual Xoose dan jangan membuat model, tabel, controller, atau route duplikat jika sudah ada.
Models & Migrations (10 tabel):
ManagedApp, AppDevice, DeviceEnrollment, ServiceDefinition, ServiceCommand, ServiceConfig, ServiceStatus, DeviceHeartbeat, ServiceLog, AppRelease.
Lengkapi dengan: Controllers (Web & API Agent), Services, Queue Jobs (driver database), Policies, Form Requests, Web/API Routes, Blade Views (8 halaman dengan Tailwind CSS 4 + Vite), dan Automated Tests.

F. SERVICE LIFECYCLE INTERFACE (PYTHON LOVEYOU)
Implementasikan antarmuka konsisten pada setiap service:
start(), stop(), pause(), resume(), restart(), get_status(), apply_config().
Setiap service wajib mendeklarasikan metadata:
service_key, display_name, supported_actions, current_status, configuration_schema, permission_requirements.
Hentikan service secara normal (graceful stop), bukan membunuh proses utama secara paksa.

G. TAHAPAN MILESTONE IMPLEMENTASI
- Milestone 0: Repository Audit (audit source aktual, config, entry point, lifecycle, inkonsistensi manifest vs config.ini, verifikasi root path — TANPA mengubah kode).
- Milestone 1: Service Refactoring (modularisasi service + BaseService + ServiceManager + schema + tests).
- Milestone 2: Device Agent (identity, enrollment, heartbeat, HTTPS polling, ack, retry, idempotency, tests).
- Milestone 3: Control Plane (10 tabel, RLS, Backend API, auth device, command queue, config versioning, audit logs).
- Milestone 4: Laravel Dashboard (8 halaman Blade + Tailwind 4 + Vite, policies, requests, tests).
- Milestone 5: End-to-End Integration (uji 1 perangkat nyata: enroll, heartbeat, STOP, ack, offline/reconnect, expired, duplicate).
- Milestone 6: Builder Integration (integrasi Agent ke template workspace di D:\KULIAH KODINGAN\xoose-loveyou\builder, uji 2 aplikasi terpisah).
- Milestone 7: Update & Hardening (release management, signed package, integrity check, rollback, revocation, docs).

H. ATURAN KERJA KETAT
1. Kerjakan SATU milestone per sesi. Jangan langsung mengerjakan seluruh milestone sekaligus.
2. Sebelum mengubah file apa pun (pada Milestone 1 dst.), tampilkan daftar file yang akan dibuat/diubah dan buat backup/Git checkpoint.
3. Jangan menghapus fitur lama dan jangan mengubah template asli tanpa persetujuan.
4. Jalankan automated test pada setiap milestone dan laporkan hasil aktualnya, bukan klaim.
5. Jika menemukan konflik arsitektur atau struktur aktual yang berbeda, berhenti dan laporkan sebelum bertindak.
6. Jangan lanjut ke milestone berikutnya sebelum acceptance criteria terpenuhi dan saya menyetujuinya.

=== INSTRUKSI SESI INI ===
MULAI SEKARANG DENGAN MILESTONE 0 SAJA.
Lakukan audit menyeluruh terhadap direktori lokal dan ketiga repository di atas.
Buat laporan lengkap di:
D:\KULIAH KODINGAN\xoose-loveyou\docs\remote-service-audit.md

JANGAN memodifikasi atau mengimplementasikan kode aplikasi apa pun pada sesi ini.
```

---

### Prompt Lanjutan per Milestone (Gunakan Setelah Milestone Sebelumnya Disetujui)

- **Milestone 1:** `Audit Milestone 0 disetujui. Lanjutkan ke MILESTONE 1 (Service Refactoring) pada D:\KULIAH KODINGAN\screenshotusingpy berdasarkan docs/remote-service-audit.md. Tampilkan daftar file yang akan diubah terlebih dahulu dan pastikan seluruh pytest lulus.`
- **Milestone 2:** `Milestone 1 selesai dan test lulus. Lanjutkan ke MILESTONE 2 (LoveYou Device Agent): implementasikan identity, enrollment, heartbeat, HTTPS polling, idempotency, acknowledgment, dan tests.`
- **Milestone 3:** `Milestone 2 selesai. Lanjutkan ke MILESTONE 3 (Control Plane & API) pada D:\laragon\www\xoose dan skema Supabase: buat migrasi 10 tabel, RLS policies, middleware device auth, API Agent, command queue, dan config versioning.`
- **Milestone 4:** `Milestone 3 selesai. Lanjutkan ke MILESTONE 4 (Laravel Dashboard): bangun 8 halaman manajemen menggunakan Blade + Tailwind CSS 4 + Vite sesuai konvensi Xoose beserta policies, form requests, dan feature tests.`
- **Milestone 5:** `Milestone 4 selesai. Lanjutkan ke MILESTONE 5 (End-to-End Integration): jalankan skenario pengujian nyata enrollment, heartbeat, perintah STOP, acknowledgment, offline/reconnect, command expired, dan duplicate command.`
- **Milestone 6:** `Milestone 5 lulus. Lanjutkan ke MILESTONE 6 (Builder Integration) pada D:\KULIAH KODINGAN\xoose-loveyou\builder: integrasikan Agent ke template workspace, inject identitas proyek tanpa shared credential, dan uji build 2 aplikasi berbeda.`
- **Milestone 7:** `Milestone 6 lulus. Lanjutkan ke MILESTONE 7 (Update & Hardening): implementasikan release management, signed package, verifikasi SHA-256, rollback, revocation lokal/remote, uji stabilitas, dan dokumentasi final.`