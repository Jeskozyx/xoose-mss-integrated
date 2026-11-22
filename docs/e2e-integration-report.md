# Milestone 5 — Laporan Pengujian End-to-End (E2E) Integrasi Xoose–LoveYou

**Tanggal Verifikasi:** 2026-11-23  
**Lingkungan:** Windows (Python 3.14.10, PHP 8.5.9, Laravel 13, SQLite terisolasi, Windows DPAPI)  
**Suite Otomatis:** `D:\KULIAH\KODINGAN\screenshotusingpy\tests\test_e2e_live_m5.py`

---

## 1. Metode Pengujian (Real Live HTTP — Tanpa Mock Backend)

Pengujian End-to-End dijalankan dengan mengeksekusi **server HTTP Laravel Xoose nyata** (`php -S 127.0.0.1:<port>` memakai `server.php` milik Laravel dengan database SQLite terisolasi yang dimigrasi & di-seed `ServiceDefinitionSeeder` + `AdminUserSeeder`) secara berdampingan dengan **LoveYou Python Device Agent & ServiceManager (7 layanan modular)** melalui komunikasi TCP/HTTP keluar (*outbound-only*) yang nyata.

---

## 2. Matriks Skenario & Hasil Aktual

| # | Skenario E2E | Alur Nyata yang Dieksekusi | Hasil |
| :--- | :--- | :--- | :--- |
| **1** | **Admin Login & Enrollment Perangkat** | Admin login ke `/login` (CSRF + session), membuat `ManagedApp` & `enrollment_code` → `LoveYouAgent` mendaftar lewat `POST /api/v1/agent/enroll` (tanpa login admin di klien) → token `xly_dev_*` disimpan terenkripsi **Windows DPAPI** (`dpapi:...`, nol plaintext di `identity.json`). | **LULUS** |
| **2** | **Heartbeat & Status `Online`** | `LoveYouAgent` mengirim `POST /api/v1/agent/heartbeat` → Xoose Admin API & halaman Blade `/remote/devices` menampilkan hostname Windows asli, status `Online`, dan `screenshot_service: Running`. | **LULUS** |
| **3** | **Remote `STOP` → Graceful Stop → Ack → `Stopped`** | Admin mengirim `STOP` lewat `POST /api/v1/admin/devices/{id}/commands` → Agent polling `GET /api/v1/agent/commands/pending`, validasi target `device_id` + `expires_at` + allowlist, memanggil `screenshot_service.stop()` secara normal, mengirim `acknowledged` → `succeeded`, serta `POST /api/v1/agent/status` → Xoose menampilkan status `Stopped` & command `succeeded`. | **LULUS** |
| **4** | **Remote `START`, Config Sync v1→v2 & Rollback (v3)** | Admin mengirim `START` → kembali `Running`; ubah runtime config `interval_seconds=11` (v1), `25` (v2), lalu rollback ke v1 (diterbitkan sebagai v3 dengan `force_apply=true`) → Agent menyelaraskan `interval_seconds=11` (`active_config_version=3`) tanpa build ulang EXE. | **LULUS** |
| **5** | **Release Check (`ReleaseUpdater`)** | Cek `/api/v1/agent/releases/latest` saat belum ada release (`release: null` → `update_available=False` tanpa error) dan sesudah Admin menerbitkan release `v1.2.0` bertanda tangan HMAC-SHA256 (`update_available=True` + checksum SHA-256). | **LULUS** |
| **6** | **Expired Command (Server & Client)** | (a) Command `pending` lewat `expires_at` otomatis ditandai `expired` oleh server saat polling dan tidak dikirimkan; (b) Command kedaluwarsa yang tiba di Agent ditolak lokal dengan status `expired` + ack `expired` ke server; `ScreenshotService` tetap `Running`. | **LULUS** |
| **7** | **Duplicate Command (Idempotency Lintas Restart)** | Payload `command_id` `STOP` yang sama dikirim ulang setelah service dijalankan lagi dan `DeviceIdentityStore` dimuat ulang dari disk → ditandai `duplicate: True`, service tetap `Running` (tidak dieksekusi ganda), dan ack idempotent dikirim ulang dengan aman. | **LULUS** |
| **8** | **Offline Outage → Reconnect Recovery** | Proses server HTTP Laravel dimatikan total → Agent mencatat `online=False`, menaikkan exponential backoff (`>= 2.0s`), menahan log pada buffer lokal, sementara layanan lokal tetap berjalan stabil → saat server hidup kembali, Agent langsung reconnect, heartbeat aktif lagi, dan log tertunda masuk ke `GET /api/v1/admin/logs`. | **LULUS** |
| **9** | **Remote Device Revocation (HTTP 401)** | Admin memanggil `POST /api/v1/admin/devices/{id}/revoke` → siklus berikutnya menerima HTTP `401` nyata dari middleware `AuthenticateDeviceAgent` → Agent menjalankan `handle_revocation()`, menghapus token DPAPI lokal (`is_revoked=True`), dan berhenti mengirim request. | **LULUS** |

---

## 3. Hardening yang Ditemukan & Diselesaikan Saat E2E

1. **`ReleaseUpdater.check_update()` (`backend/agent/updater.py`)**: Ditambahkan penjagaan tipe ketika server mengembalikan `{"release": null}` (belum ada release aktif) agar tidak memicu `AttributeError`.
2. **`CommandExecutor.execute_command()` (`backend/agent/command_executor.py`)**: Saat menerima `command_id` duplikat yang sudah tercatat di ledger lokal (`processed_commands.json`), Agent kini turut mengirim ulang *idempotent ack* ke server agar command yang ack-nya sempat hilang saat jaringan putus dapat ditutup bersih di Control Plane.

---

## 4. Ringkasan Hasil Pengujian Lintas Repository

- **LoveYou Client & Live E2E (`D:\KULIAH\KODINGAN\screenshotusingpy`)**: `python -m pytest -v` → **19 passed in 16.93s**
- **Laravel Xoose Control Plane & Dashboard (`D:\laragon\www\xoose`)**: `php artisan test` → **35 passed (256 assertions)**
- **Python Build Engine (`D:\KULIAH\KODINGAN\xoose-loveyou\builder`)**: `python -m unittest discover -s tests -v` → **11 passed in 0.801s**

---

## 5. Cara Menjalankan Ulang Uji E2E Kapan Saja

```powershell
Set-Location D:\KULIAH\KODINGAN\screenshotusingpy
python -m pytest -v tests/test_e2e_live_m5.py
```
