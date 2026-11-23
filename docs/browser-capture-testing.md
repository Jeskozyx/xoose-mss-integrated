# Specific Screen Xoose–LoveYou: Laporan Uji Akhir (BC-7), Panduan Admin & Pengguna, Troubleshooting, & Release/Rollback (BC-8)

**Tanggal:** 23 November 2026  
**Status:** Milestone BC-0 s.d. BC-8 Selesai & Terverifikasi  
**Root Integrasi Aktual:** `D:\KULIAH\KODINGAN\xoose-loveyou`  
**LoveYou Client:** `D:\KULIAH\KODINGAN\screenshotusingpy`  
**Laravel Xoose:** `D:\laragon\www\xoose`

---

## 1. Ringkasan Eksekutif & Hasil Pengujian Menyeluruh (BC-7)

Seluruh komponen **Specific Screen & Browser Domain Capture** telah diuji secara unit, integrasi, dan *End-to-End (E2E)* live menggunakan server Laravel Xoose nyata, LoveYou Device Agent, dan binary Native Messaging Host hasil kompilasi `PyInstaller --onedir` (`xoose-native-host.exe`):

| Lapisan / Repository | Perintah Uji | Hasil | Cakupan Utama |
| :--- | :--- | :---: | :--- |
| **Browser Extension** (`xoose-loveyou/browser-extension`) | `npm run lint && npm test` | **13 / 13 PASSED** | Manifest MV3 Chromium & Firefox, Domain Matcher ketat, Active Tab, Focus/Tab/Origin Guard, Pause/Stop lokal, Live Config Update, Permission Revoke, Native Host Disconnect, Multi-Chunk SHA-256 |
| **Native Messaging Host** (`xoose-loveyou/native-host`) | `python -m pytest -v` | **11 / 11 PASSED** | Framing 32-bit binary-safe, allowlist pesan, penolakan `shell`/`output_path`, chunk out-of-order, duplikat, hilang/timeout, SHA-256 mismatch, path traversal, host restart, `stdout` 100% bersih |
| **Builder & Bundler** (`xoose-loveyou/builder`) | `python -m pytest -v` + `bundle-browser-capture` | **17 / 17 PASSED (+12 subtests)** | Bundling Extension Chromium & Firefox (+ ZIP), kompilasi `PyInstaller --onedir` `xoose-native-host.exe` + stdio smoke test (`['hello_ack', 'config_update', 'pong']`), guard anti-kebocoran secret |
| **LoveYou Client & Live E2E BC-7** (`screenshotusingpy`) | `python -m pytest -v` | **25 / 25 PASSED** | Lifecycle `BrowserCaptureService`, atomic spool → `SyncService` (`source=browser_tab`), live switch 4 mode, filter foreground MSS (`GetForegroundWindow`), regresi 20 test MSS/Agent/Updater + Live E2E BC-7 (server Laravel + Agent + `xoose-native-host.exe` + rollback + offline/reconnect) |
| **Laravel Xoose Dashboard** (`D:\laragon\www\xoose`) | `php artisan test --compact` | **43 / 43 PASSED (328 assertions)** | Auth admin, policy kepemilikan, live mode switcher, CRUD domain/window rules, validasi ketat (tolak wildcard/scheme/path/port), versioning & rollback, sinkronisasi Agent API `/api/v1/agent/configs` |

> **Status Browser Lokal:**  
> - **Google Chrome (`v157.0.8103.79`):** Terpasang lokal; diverifikasi secara live (headless Chrome render `/remote/capture-rules`, popup ekstensi, serta automated tests).  
> - **Microsoft Edge & Mozilla Firefox:** Belum terpasang binary desktop-nya di mesin lokal ini; keduanya diverifikasi penuh melalui *automated WebExtensions adapter tests*, validasi manifest MV3/Gecko, template host manifest (`allowed_origins` & `allowed_extensions`), dan *dry-run* HKCU registry installer. Gunakan checklist Bagian 2.2 saat menguji langsung di mesin dengan Edge/Firefox terpasang.

---

## 2. Matriks Pengujian Wajib (Mandatory Test Matrix)

### 2.1 Verifikasi Otomatis Terpenuhi

| Kategori Uji | Skenario | Status | Bukti Test |
| :--- | :--- | :---: | :--- |
| **Domain Matcher** | Root domain cocok (`konstantaedu.com`) & semua path (`/`, `/tryout`, `/ujian/123?a=1#b`) | **LULUS** | `tests/domain-matcher.test.js` |
| **Domain Matcher** | `www.` & subdomain cocok bila `include_subdomains: true`, ditolak bila `false` | **LULUS** | `tests/domain-matcher.test.js` |
| **Domain Matcher** | Domain mirip palsu (`konstantaedu.com.evil.com`, `notkonstantaedu.com`) ditolak | **LULUS** | `tests/domain-matcher.test.js` |
| **Domain Matcher** | URL invalid & skema internal (`chrome://`, `edge://`, `about:`, `file://`, `moz-extension://`) ditolak | **LULUS** | `tests/domain-matcher.test.js` |
| **Browser Policy** | Active tab capture lintas Chrome, Edge, Firefox + chunked SHA-256 | **LULUS** | `tests/capture-policy.test.js` |
| **Browser Policy** | Jeda saat browser hilang fokus, pindah tab, navigasi domain lain, atau pindah origin (`local_start`) | **LULUS** | `tests/capture-policy.test.js` |
| **Browser Policy** | Kontrol **Pause/Stop lokal**, pencabutan izin `<all_urls>`, & pemutusan Native Host | **LULUS** | `tests/capture-policy.test.js` |
| **Native Messaging** | Pesan valid/invalid, chunk hilang/timeout, duplikat, urutan acak, SHA-256 salah, melebihi batas, host restart, & `stdout` bersih | **LULUS** | `native-host/tests/test_protocol.py` & `test_image_assembler.py` |
| **Live E2E BC-7** | Admin ganti `active_source` & domain secara live saat LoveYou & `xoose-native-host.exe` sedang berjalan (tanpa rebuild EXE) | **LULUS** | `tests/test_e2e_browser_capture_bc7.py` |
| **Live E2E BC-7** | Upload spool → `SyncService` (`source=browser_tab`), status live di `service_status`, audit `service_logs`, rollback, & offline/reconnect | **LULUS** | `tests/test_e2e_browser_capture_bc7.py` |
| **Xoose & Regresi MSS** | CRUD & rollback rule, otorisasi admin, validasi input, dan 100% regresi `ScreenshotService` MSS lama | **LULUS** | `CaptureRuleManagementTest.php` & `test_services_m1.py` |

### 2.2 Checklist Uji Manual pada Browser Edge & Firefox (Jika Dipasang di Mesin Target)
1. Muat `extensions/chromium` di `edge://extensions` (Developer Mode → Load Unpacked) → salin 32 karakter Edge Extension ID.
2. Muat `extensions/firefox/manifest.json` di `about:debugging#/runtime/this-firefox` (Load Temporary Add-on).
3. Jalankan `install-host.ps1 -EdgeExtensionId "<ID>" -FirefoxAddonId "loveyou-capture@xoose.local"`.
4. Buka popup ekstensi → pastikan status **Native Host: Terhubung** → buka `https://konstantaedu.com` → klik **Mulai** → verifikasi badge `ON` & tangkapan masuk ke Supabase dengan prefix `browser_edge_` / `browser_firefox_`.

---

## 3. Panduan Singkat Admin (Xoose Dashboard)

1. Login ke Xoose (`http://127.0.0.1:8000/login`), lalu buka sidebar **Remote Manager → Capture Rules** (`/remote/capture-rules`).
2. **Pilih Scope Target:**
   - Klik **`App: <NamaApp>`** untuk menerapkan aturan secara massal ke seluruh perangkat aplikasi tersebut.
   - Klik **`Device: <Hostname>`** untuk menerapkan aturan khusus (*override*) pada 1 perangkat saja.
3. **Tambahkan Aturan Domain Target:**
   - Isi **Domain Target** bersih tanpa `https://` atau `*`, contoh: `konstantaedu.com`.
   - Centang **Sertakan Subdomain** jika ingin mencakup `www.konstantaedu.com` dan subdomain lainnya.
   - Pilih browser target (`Chrome`, `Edge`, `Firefox`), lalu klik **`+ Simpan Aturan Domain (Live)`**.
4. **Aktifkan / Ganti Target Secara Live (Tanpa Rebuild EXE):**
   - Pada kartu **Live Capture Target Switcher**, pilih salah satu mode:
     - **`Browser Domain`:** Menangkap isi tab aktif browser saja sesuai daftar domain.
     - **`Application Window`:** Menangkap via MSS hanya saat proses/judul jendela tertentu di depan (tanpa perlu Browser Extension).
     - **`Desktop MSS`:** Menangkap layar penuh klasik.
     - **`Disabled`:** Menghentikan sementara seluruh capture.
   - Atur interval detik, format gambar (`webp`), dan mode izin (`local_start` default / `automatic_domain`), lalu klik **`Terapkan Kebijakan Live`**.
   - Setiap perubahan menaikkan `config_version` (misal `v1` → `v2`) dan otomatis diterima oleh LoveYou Agent dalam ≤ 60 detik (atau instan lewat perintah restart/reload config).
5. **Pantau & Rollback:**
   - Panel kanan **Status Live Extension & Agent** menampilkan status koneksi extension, browser aktif, izin (`activeTab` vs `<all_urls>`), domain cocok, versi config, dan error terakhir.
   - Panel **Riwayat Versi & Rollback** memungkinkan pemulihan 1-klik ke versi sebelumnya kapan saja.

---

## 4. Panduan Pengguna Perangkat

1. **Instalasi Sekali Saja:** Jalankan aplikasi LoveYou (`.exe`), muat ekstensi **Xoose-LoveYou Browser Capture** pada browser pilihan, dan jalankan `install-host.ps1` dengan Extension ID yang sesuai (lihat [native-messaging-installation.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/docs/native-messaging-installation.md)).
2. **Transparansi & Kontrol Lokal:**
   - Klik ikon **Xoose Capture** di toolbar browser untuk melihat status, domain aktif, mode izin, dan koneksi Native Host.
   - Pada mode **Local-Start (Default)**, klik **Mulai** saat berada di tab target.
   - Klik **Jeda** atau **Hentikan** kapan saja di popup ekstensi (atau dari menu klik-kanan System Tray LoveYou) untuk langsung menjeda/menghentikan capture.
   - Untuk mengizinkan *Automatic Domain Mode*, klik tautan **Izinkan Mode Otomatis** dan setujui dialog resmi browser (`<all_urls>`). Izin ini dapat dicabut kapan saja melalui tombol **Cabut Izin Otomatis**.

---

## 5. Panduan Troubleshooting

| Gejala | Penyebab Umum | Solusi |
| :--- | :--- | :--- |
| Popup menampilkan **`Host Putus`** (`!`) | Registry HKCU belum terdaftar atau Extension ID di manifest tidak cocok dengan ID di `chrome://extensions` | Jalankan ulang `install-host.ps1 -ChromeExtensionId "<ID_AKTUAL>"`, lalu klik **Hubungkan** di popup |
| Status **`Bukan Target`** meski membuka website yang benar | Salah ketik domain, skema `http://` saat rule hanya `https`, atau `include_subdomains` nonaktif saat membuka `www.` | Cek ejaan domain, aktifkan **Sertakan Subdomain**, dan pastikan skema URL sesuai di `/remote/capture-rules` |
| Status **`Jeda (Origin)`** setelah berpindah halaman | Mode izin masih `local_start` (`activeTab`) sehingga izin berakhir saat pindah origin/subdomain | Klik **Mulai** lagi di tab baru, atau aktifkan **Izinkan Mode Otomatis** (`<all_urls>`) pada popup |
| Gambar tidak muncul di Supabase | `SyncService` dalam status `Paused`/`Stopped`, atau perangkat sedang offline | Cek status `sync_service` di `/remote/devices/{id}`; saat online kembali antrean otomatis dikirim ulang |
| Native Host crash dengan error JSON di browser | `stdout` tercemar output non-protokol | Pastikan tidak ada `print()` di `host.py` dan gunakan mode `--console` pada `PyInstaller --onedir`; periksa log di `%LOCALAPPDATA%\XooseLoveYouAgent\logs\native-host.log` |

---

## 6. Prosedur Release Versioning & Rollback

1. **Build Paket Rilis Baru:**
   ```powershell
   cd "D:\KULIAH\KODINGAN\xoose-loveyou\builder"
   python -m xoose_builder.cli bundle-browser-capture --bundle-id v1.1.0
   ```
2. **Catat SHA-256 & Publikasikan Release:**
   Ambil `sha256_checksum` dari `builds\browser-capture\bundle_v1.1.0\bundle-manifest.json` (atau hitung menggunakan `python -m xoose_builder.cli sign --file <artefak>`), lalu terbitkan melalui halaman Xoose **Releases & Updates** (`/remote/releases`) yang otomatis menandatanganinya dengan **HMAC-SHA256**.
3. **Prosedur Rollback Cepat:**
   - **Rollback Konfigurasi Live:** Klik tombol **Rollback** di panel *Riwayat Versi & Rollback* pada `/remote/capture-rules` → menerbitkan versi baru dengan flag `force_apply = true` yang langsung dipulihkan oleh LoveYou Agent & Extension.
   - **Rollback Versi Aplikasi:** Klik tombol **Aktifkan** pada versi rilis sebelumnya di `/remote/releases`.
   - **Uninstall Bersih Native Host:** Jalankan `powershell -ExecutionPolicy Bypass -File "D:\KULIAH\KODINGAN\xoose-loveyou\native-host\install\uninstall-host.ps1"`.
