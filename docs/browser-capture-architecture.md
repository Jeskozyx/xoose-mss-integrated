# Specific Screen Xoose–LoveYou: Arsitektur Teknis, Domain Matcher Spec, Kontrak Native Messaging & Browser Compatibility Matrix

**Milestone:** BC-1 — Desain & Schema  
**Tanggal:** 23 November 2026  
**Referensi Audit:** [browser-capture-audit.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/docs/browser-capture-audit.md)  
**Dokumen Pendamping:** [browser-permissions.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/docs/browser-permissions.md) | [browser_capture.json](file:///D:/KULIAH/KODINGAN/screenshotusingpy/backend/schemas/browser_capture.json)

---

## 0. Keputusan Desain Terkunci (Disetujui Pasca Audit BC-0)

1. **Root Path Aktual:** Seluruh kode, script, manifest, dan konfigurasi menggunakan `D:\KULIAH\KODINGAN\xoose-loveyou`, `D:\KULIAH\KODINGAN\screenshotusingpy`, dan `D:\laragon\www\xoose`.
2. **Dukungan 3 Browser:** Extension, host manifest, HKCU registry installer, dan automated tests dibangun penuh untuk **Google Chrome**, **Microsoft Edge**, dan **Mozilla Firefox**. Uji live browser E2E di mesin lokal berjalan penuh pada Chrome (dan Edge/Firefox bila terpasang; jika belum, dilengkapi automated test + prosedur uji manual).
3. **Zero New DB Tables:** Konfigurasi disimpan pada `service_definitions` & `service_configs` eksisting dengan `service_key = "browser_capture_service"`, disertai perluasan validasi rekursif object/array di `ConfigVersionService`.
4. **Metadata Supabase `hasil_ss` Backward-Compatible:** `SyncService` & `SupabaseLogger.log_record()` menggunakan pola *graceful fallback* (mencoba kolom metadata terstruktur bila tersedia, otomatis fallback ke tag terstruktur pada `notes` & `active_window` + prefix file `browser_<browser>_...`), sehingga tidak pernah gagal `PGRST204`.
5. **User-Scoped Shared Bridge IPC (Tanpa Port HTTP Lokal):** Komunikasi antara proses desktop `LoveYou Agent` dan child process browser `native-host/host.py` memakai direktori terisolasi `%LOCALAPPDATA%\XooseLoveYouAgent\bridge\` dengan *atomic file write/rename* (`runtime_config.json`, `host_status_<browser>.json`, `control_signal.json`, `spool/incoming/`).
6. **Pipeline WEBP Deterministik:** Karena `tabs.captureVisibleTab()` hanya mendukung parameter native `png`/`jpeg`, konversi ke `webp` dilakukan via `OffscreenCanvas` (bila tersedia) atau `Pillow` saat assembly di `image_assembler.py`, dengan fallback otomatis ke `png`.
7. **Indikator & Kontrol Lokal Minimalis:** Badge extension, popup status/Pause/Stop lokal, dan menu System Tray LoveYou dirancang ringkas, tenang, dan minimalis tanpa overlay intrusif pada halaman web, dengan tetap menjaga transparansi penuh dan kontrol lokal pengguna.

---

## 1. Arsitektur End-to-End & Live Runtime Selection

### 1.1 Topologi Komponen

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 1. XOOSE CONTROL PLANE (D:\laragon\www\xoose — Laravel 13.43)              │
│    • Capture Rules Manager (/remote/capture-rules)                         │
│    • CaptureRuleConfigService → ConfigVersionService (service_configs)     │
│    • service_key = "browser_capture_service" (App default / Device override)│
│    • Agent API eksisting: GET /api/v1/agent/configs & POST /api/v1/agent/status │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │ Outbound HTTPS (Bearer Device Token)
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 2. LOVEYOU DESKTOP AGENT (D:\KULIAH\KODINGAN\screenshotusingpy)            │
│    • ConfigSyncManager mengambil config_version terbaru saat runtime       │
│    • CaptureModeCoordinator menyelaraskan active_source secara live:       │
│        - browser_domain     → BrowserCaptureService aktif, MSS paused      │
│        - application_window → MSS aktif dgn filter foreground window/proc  │
│        - desktop_mss        → MSS aktif penuh (perilaku eksisting)         │
│        - disabled           → BrowserCaptureService & MSS nonaktif         │
│    • NativeBridge menulis runtime_config.json & membaca host_status_*.json │
└──────────────────┬───────────────────────────────────┬─────────────────────┘
                   │ Atomic File IPC                   │ Internal Lifecycle
                   │ (%LOCALAPPDATA%\XooseLoveYouAgent\bridge\)
                   ▼                                   ▼
┌─────────────────────────────────────────┐ ┌────────────────────────────────┐
│ 3A. NATIVE MESSAGING HOST (host.py)     │ │ 3B. SCREENSHOT SERVICE (MSS)   │
│     • Di-spawn oleh Browser (stdin/out) │ │     • Tetap utuh & terpisah    │
│     • 32-bit length-prefixed JSON       │ │     • Mode desktop_mss /       │
│     • Watch runtime_config.json → push  │ │       application_window       │
│     • Chunk assembly + SHA-256 + WEBP   │ │       (ctypes GetForegroundWin)│
│     • Atomic spool → spool/incoming/    │ └───────────────┬────────────────┘
└──────────────────┬──────────────────────┘                 │
                   │ WebExtensions Native Messaging         │
     ┌─────────────┼─────────────┐                          │
     ▼             ▼             ▼                          │
 [Chrome]       [Edge]       [Firefox]                      │
 MV3 SW         MV3 SW       MV3 Gecko                      │
 • tabs.captureVisibleTab() + URL Domain Matcher            │
 • alarms scheduler + focus/tab guard + minimalist badge    │
                   │                                        │
                   ▼ (BrowserCaptureService consumes spool) │
┌────────────────────────────────────────────────────────────────────────────┐
│ 4. SYNC SERVICE → SUPABASE STORAGE & TABEL hasil_ss                        │
│    • Queue offline-safe + exponential backoff + pembersihan file spool     │
│    • Pemisahan metadata source: browser_tab vs application_window vs desktop_mss │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 State Machine Koordinasi Live `active_source`

Admin dapat mengganti `capture_policy.active_source` kapan saja saat LoveYou sedang berjalan:

| `capture_policy.active_source` | `browser_capture.enabled` | `window_capture.enabled` | Perilaku `BrowserCaptureService` | Perilaku `ScreenshotService` (MSS) |
| :--- | :--- | :--- | :--- | :--- |
| **`disabled`** | *(diabaikan → nonaktif)* | *(diabaikan → nonaktif)* | Mengirim `enabled: false` ke bridge; tidak capture | Dijeda / berhenti (`Paused` atau `Stopped`) |
| **`browser_domain`** | `true` | *(diabaikan)* | Aktif; push rule domain ke bridge/extension; konsumsi spool → `SyncService` | Otomatis dijeda (`Paused`) agar tidak terjadi duplikasi capture |
| **`browser_domain`** | `false` *(default aman)* | `false` | Standby (`Stopped`/`Paused`); tidak capture | Tidak memulai capture browser; jika belum pernah dikonfigurasi remote, mempertahankan mode default startup |
| **`application_window`** | *(diabaikan → nonaktif)* | `true` | Mengirim `enabled: false` ke bridge | Aktif dengan `window_filter` (`GetForegroundWindow()` + nama proses `.exe` + substring judul); skip capture jika foreground tidak cocok |
| **`desktop_mss`** | *(diabaikan → nonaktif)* | *(diabaikan)* | Mengirim `enabled: false` ke bridge | Aktif penuh menangkap desktop (perilaku MSS klasik) |

> **Jaminan Backward Compatibility:** Jika `browser_capture_service` belum pernah dikonfigurasi oleh admin (`config_version == 0` dan `browser_capture.enabled == false`), `ScreenshotService` tetap menjalankan perilaku bawaan lama tanpa regresi pada 20 unit test eksisting.

---

## 2. Spesifikasi Ketat Domain Matcher (`domain-matcher.js`)

### 2.1 Prinsip Dasar
- **DILARANG** menggunakan `url.includes()`, `url.indexOf()`, atau pencocokan regex substring longgar.
- **WAJIB** mem-parse URL menggunakan standar WHATWG `new URL(rawUrl)`.
- Semua pencocokan dilakukan pada `url.protocol` dan `url.hostname` yang telah dinormalisasi.

### 2.2 Skema Internal & Non-Web yang Wajib Ditolak
Setiap URL dengan salah satu skema berikut (atau gagal di-parse oleh `new URL()`) **WAJIB ditolak** (`matched: false`, `reason: "disallowed_scheme"` / `"invalid_url"`):
- `chrome:`, `chrome-extension:`, `chrome-search:`, `chrome-untrusted:`
- `edge:`, `extension:`
- `about:`, `moz-extension:`, `resource:`, `jar:`
- `file:`, `ftp:`, `data:`, `blob:`, `javascript:`, `view-source:`, `devtools:`

### 2.3 Algoritma Normalisasi & Evaluasi
1. **Validasi Input:** Jika `rawUrl` kosong, bukan string, atau melebihi 4096 karakter → tolak (`invalid_url`).
2. **Parse URL:**
   ```js
   let parsed;
   try { parsed = new URL(rawUrl); } catch { return reject("invalid_url"); }
   ```
3. **Normalisasi Scheme:**
   - `scheme = parsed.protocol.replace(/:$/, "").toLowerCase()` (contoh: `"https"`, `"http"`).
   - Tolak jika `scheme` tidak termasuk `{"http", "https"}`.
4. **Normalisasi Hostname Tab:**
   - `rawHost = parsed.hostname.toLowerCase().trim()`.
   - Hapus *trailing dot* FQDN: `host = rawHost.replace(/\.+$/, "")`.
   - Catatan: `URL.hostname` sudah otomatis menghapus nomor port (`:8080`, `:443`) dan mengubah karakter IDN menjadi Punycode ASCII (`xn--...`).
   - Tolak jika `host` kosong, mengandung spasi, berisi `..`, atau berupa alamat IP mentah (IPv4/IPv6) kecuali secara eksplisit cocok dan valid.
5. **Normalisasi Domain Rule:**
   - `ruleDomain = rule.domain.toLowerCase().trim().replace(/\.+$/, "")`.
   - Rule valid hanya boleh berisi label DNS ASCII valid (`^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$`). Wildcard (`*`), path (`/`), scheme (`https://`), dan port (`:443`) **ditolak saat validasi konfigurasi**.
6. **Filter Browser & Rule Aktif:**
   - Hanya evaluasi rule dengan `rule.enabled === true` dan `rule.browsers.includes(currentBrowser)`.
   - Evaluasi skema: `allowedSchemes = rule.schemes?.length ? rule.schemes : ["https"]`. Tolak jika `!allowedSchemes.includes(scheme)`.
7. **Pencocokan Batas Label DNS (Strict Boundary Match):**
   - **Exact root match:** `host === ruleDomain` → **COCOK**.
   - **Subdomain match** (hanya jika `rule.include_subdomains === true`): `host.endsWith("." + ruleDomain)` → **COCOK**.
   - **Konsekuensi Keamanan:**
     - `konstantaedu.com` → cocok dengan `konstantaedu.com`, `konstantaedu.com/`, `konstantaedu.com/tryout`, `konstantaedu.com/ujian/123?token=abc#sec`.
     - Jika `include_subdomains: true`: cocok dengan `www.konstantaedu.com`, `portal.konstantaedu.com/login`, `a.b.konstantaedu.com`.
     - Jika `include_subdomains: false`: `www.konstantaedu.com` dan `sub.konstantaedu.com` **DITOLAK**.
     - `konstantaedu.com.evil.com`, `notkonstantaedu.com`, `fake-konstantaedu.com` → **SELALU DITOLAK** (gagal boundary check).
8. **Privasi Metadata URL:**
   - Output metadata hanya menyimpan `origin_domain = host` (dan `scheme`). **Query string (`?token=...`) dan fragment (`#...`) TIDAK PERNAH dikirim** dalam metadata capture secara default.

### 2.4 Vektor Uji Kanonik Domain Matcher

| URL Uji | Rule (`domain: "konstantaedu.com"`, `schemes: ["https"]`) | `include_subdomains` | Hasil Wajib |
| :--- | :--- | :---: | :---: |
| `https://konstantaedu.com` | Aktif | `false` | **MATCH** |
| `https://konstantaedu.com/ujian/123?secret=1#top` | Aktif | `false` | **MATCH** (`origin_domain: "konstantaedu.com"`, tanpa query/hash) |
| `https://KONSTANTAEDU.COM.:443/tryout` | Aktif | `false` | **MATCH** (normalisasi lowercase, trailing dot, port) |
| `https://www.konstantaedu.com/tryout` | Aktif | `true` | **MATCH** |
| `https://sub.a.konstantaedu.com/page` | Aktif | `true` | **MATCH** |
| `https://www.konstantaedu.com/tryout` | Aktif | `false` | **REJECT** |
| `https://konstantaedu.com.evil.com/tryout` | Aktif | `true` | **REJECT** |
| `https://mykonstantaedu.com/` | Aktif | `true` | **REJECT** |
| `http://konstantaedu.com/` | Aktif (`schemes: ["https"]`) | `true` | **REJECT** |
| `chrome://extensions/` | Aktif | `true` | **REJECT** |
| `edge://settings/` | Aktif | `true` | **REJECT** |
| `about:debugging` | Aktif | `true` | **REJECT** |
| `file:///C:/konstantaedu.com/index.html` | Aktif | `true` | **REJECT** |
| `not-a-valid-url` | Aktif | `true` | **REJECT** |

---

## 3. JSON Schema Live Capture Selection (`browser_capture_service`)

Skema kanonik tersimpan di [backend/schemas/browser_capture.json](file:///D:/KULIAH/KODINGAN/screenshotusingpy/backend/schemas/browser_capture.json) (Draft 2020-12) dan menjadi sumber kebenaran tunggal untuk Laravel (`ConfigVersionService` & `CaptureRuleConfigService`), LoveYou (`Pydantic`), dan Browser Extension (`config-validator.js`).

### 3.1 Ringkasan Struktur & Batasan Validasi

| Path Field | Tipe | Default | Aturan Validasi Ketat |
| :--- | :--- | :--- | :--- |
| `capture_policy.active_source` | `string` (enum) | `"desktop_mss"` *(atau `"disabled"` bila baru dikonfigurasi browser)* | Wajib salah satu dari: `disabled`, `browser_domain`, `application_window`, `desktop_mss` |
| `capture_policy.allow_live_switch` | `boolean` | `true` | Mengizinkan pergantian mode tanpa restart/rebuild |
| `browser_capture.enabled` | `boolean` | **`false`** *(WAJIB)* | Default selalu nonaktif sampai admin mengaktifkan |
| `browser_capture.capture_mode` | `string` (enum) | `"active_tab"` | Hanya `"active_tab"` (tab latar belakang dilarang) |
| `browser_capture.permission_mode` | `string` (enum) | `"local_start"` | `"local_start"` (default, `activeTab`) atau `"automatic_domain"` (`<all_urls>`) |
| `browser_capture.local_session_required` | `boolean` | `true` | Wajib sesi lokal aktif / tidak di-stop pengguna |
| `browser_capture.pause_when_browser_unfocused` | `boolean` | `true` | Jeda otomatis saat jendela browser tidak fokus |
| `browser_capture.pause_when_tab_inactive` | `boolean` | `true` | Jeda otomatis saat tab tidak aktif |
| `browser_capture.image_format` | `string` (enum) | `"webp"` | `"webp"` atau `"png"` |
| `browser_capture.fallback_format` | `string` (enum) | `"png"` | `"png"` atau `"jpeg"` |
| `browser_capture.capture_interval_seconds` | `integer` | `10` | Minimum `2`, maksimum `3600` |
| `browser_capture.rules` | `array<object>` | `[]` | Maksimum `50` rule; setiap `id` unik (`^[a-z0-9][a-z0-9_-]{1,63}$`); `domain` DNS valid tanpa scheme/wildcard/path; `include_subdomains` boolean; `schemes` subset `["https", "http"]` (min 1, default `["https"]`); `browsers` subset `["chrome", "edge", "firefox"]` (min 1) |
| `window_capture.enabled` | `boolean` | `false` | Default nonaktif |
| `window_capture.capture_mode` | `string` (enum) | `"active_window"` | Hanya `"active_window"` |
| `window_capture.capture_interval_seconds` | `integer` | `10` | Minimum `2`, maksimum `3600` |
| `window_capture.rules` | `array<object>` | `[]` | Maksimum `50` rule; `id` unik; `process` nama file `.exe` aman (`^[a-zA-Z0-9._-]{1,120}$`, tanpa path separator); `window_title_contains` string max 200 karakter |

---

## 4. Kontrak Protokol Native Messaging & Chunked Transfer

### 4.1 Aturan Framing & Kebersihan Stream
- **Transport:** `stdin` (Browser → Host) dan `stdout` (Host → Browser) dalam mode **binary** (`sys.stdin.buffer`, `sys.stdout.buffer` di Python Windows dengan `msvcrt.setmode(..., os.O_BINARY)` agar tidak terjadi konversi `\n` → `\r\n` yang merusak header length!).
- **Framing:** Header 4 byte unsigned integer 32-bit little-endian (`struct.pack("<I", len(body))`) diikuti payload JSON UTF-8.
- **Batas Ukuran Frame:**
  - Host → Extension: maksimum **512 KB** (batas keras browser adalah 1 MB; 512 KB memberi margin aman).
  - Extension → Host: setiap pesan chunk dibatasi maksimum **256 KB** payload Base64 (maksimum raw decoded image **10 MB**, maksimum **64 chunk** per capture).
- **Aturan `stdout`:** `stdout` **100% eksklusif untuk frame Native Messaging**. Seluruh log debug/error host wajib ditulis ke `stderr` dan file log (`%LOCALAPPDATA%\XooseLoveYouAgent\logs\native-host.log`).

### 4.2 Katalog Pesan (Extension ↔ Native Host)

#### A. Extension → Native Host
1. **`hello`** (dikirim tepat setelah `connectNative`):
   ```json
   {
     "type": "hello",
     "protocol_version": 1,
     "browser": "chrome",
     "extension_id": "<runtime.id>",
     "extension_version": "1.0.0"
   }
   ```
2. **`get_config`** / **`ping`**:
   ```json
   { "type": "get_config", "current_config_version": 0 }
   { "type": "ping", "ts": "2026-11-23T13:00:00Z" }
   ```
3. **`status_report`** (dikirim saat status sesi, izin, tab cocok, atau error berubah):
   ```json
   {
     "type": "status_report",
     "browser": "chrome",
     "extension_connected": true,
     "permission_mode": "local_start",
     "has_host_permission": false,
     "local_session_state": "running",
     "capture_state": "capturing",
     "active_rule_id": "konstanta-domain",
     "matched_domain": "www.konstantaedu.com",
     "config_version": 3,
     "captures_sent": 12,
     "last_capture_at": "2026-11-23T13:05:10Z",
     "last_error": null
   }
   ```
4. **`capture_chunk`** (transfer gambar terpotong):
   ```json
   {
     "type": "capture_chunk",
     "capture_id": "550e8400-e29b-41d4-a716-446655440000",
     "chunk_index": 0,
     "chunk_count": 3,
     "mime_type": "image/png",
     "target_format": "webp",
     "payload": "<base64-slice>",
     "checksum": "<sha256-hex-of-complete-raw-image-bytes>",
     "meta": {
       "source": "browser_tab",
       "browser": "chrome",
       "rule_id": "konstanta-domain",
       "origin_domain": "www.konstantaedu.com",
       "captured_at": "2026-11-23T13:05:10Z"
     }
   }
   ```
5. **`capture_abort`** (membatalkan assembly yang terhenti di tengah jalan):
   ```json
   { "type": "capture_abort", "capture_id": "550e8400-e29b-41d4-a716-446655440000", "reason": "tab_switched" }
   ```

#### B. Native Host → Extension
1. **`hello_ack`**:
   ```json
   { "type": "hello_ack", "protocol_version": 1, "host_version": "1.0.0", "spool_ready": true }
   ```
2. **`config_update`** (di-push segera saat `runtime_config.json` berubah atau merespons `get_config`):
   ```json
   {
     "type": "config_update",
     "config_version": 4,
     "active_source": "browser_domain",
     "browser_capture": { "...": "..." }
   }
   ```
3. **`control_action`** (perintah lokal dari LoveYou Tray / remote command, hanya allowlist):
   ```json
   { "type": "control_action", "action": "pause", "source": "loveyou_tray", "seq": 5 }
   ```
   *(Allowlist `action`: `"pause"`, `"resume"`, `"stop"`, `"sync_config"` — tidak pernah shell/exec).*
4. **`capture_ack`** / **`capture_error`**:
   ```json
   { "type": "capture_ack", "capture_id": "550e8400-...", "status": "spooled", "mime_type": "image/webp", "image_checksum": "<sha256-final-file>" }
   { "type": "capture_error", "capture_id": "550e8400-...", "code": "CHECKSUM_MISMATCH", "message": "SHA-256 tidak cocok." }
   ```

### 4.3 Validasi Keamanan & Atomic Spool (`image_assembler.py`)
- **Validasi Origin/Identitas:** Browser memvalidasi `allowed_origins` (Chrome/Edge) atau `allowed_extensions` (Firefox) dari manifest registry HKCU. Host tetap menolak tipe pesan di luar allowlist dan menolak `capture_id` yang bukan UUID valid (mencegah path traversal).
- **Larangan Mutlak:** Host **tidak menerima** `output_path`, shell command, atau URL arbitrer dari extension.
- **Assembly Guards:**
  - Cek `0 <= chunk_index < chunk_count <= 64`.
  - Cek duplikasi chunk (`chunk_index` sudah diterima → tolak/error `DUPLICATE_CHUNK`).
  - Cek batas ukuran tiap chunk (≤ 350 KB base64) dan total byte (≤ 10 MB).
  - Timeout assembly **30 detik** (buffer stale otomatis dibersihkan agar tidak bocor memori).
  - Verifikasi **SHA-256** hasil gabungan byte mentah sebelum decoding.
  - Verifikasi magic bytes/gambar valid melalui `Pillow`; jika `target_format == "webp"` dan input berupa `png`/`jpeg`, konversi ke `webp` (quality 75, fallback ke `png` bila gagal), lalu hitung `image_checksum` file final.
- **Atomic Rename ke `spool/incoming/`:**
  1. Tulis gambar ke `spool/tmp/<capture_id>.<ext>.tmp` lalu `os.replace()` ke `spool/incoming/<capture_id>.<ext>`.
  2. Tulis metadata ke `spool/tmp/<capture_id>.meta.json.tmp` lalu `os.replace()` ke `spool/incoming/<capture_id>.meta.json`.
  3. `BrowserCaptureService` hanya membaca file pasangan yang `.meta.json`-nya sudah utuh (atomic), sehingga `SyncService` tidak pernah membaca file setengah jadi.

---

## 5. Kontrak Shared Bridge IPC (`LoveYou Agent` ↔ `Native Host`)

Lokasi default runtime Windows: `%LOCALAPPDATA%\XooseLoveYouAgent\bridge\` (dapat di-override via env `XOOSE_BRIDGE_DIR` untuk pengujian terisolasi `pytest`).

| File / Folder di Bridge Dir | Penulis (Atomic `os.replace`) | Pembaca | Fungsi |
| :--- | :--- | :--- | :--- |
| `runtime_config.json` | `LoveYou Agent` (`NativeBridge`) | `native-host/host.py` (poll mtime tiap 1 detik) | Menyimpan `config_version`, `device_id`, `active_source`, dan objek `browser_capture` terbaru untuk di-push live ke semua browser yang terhubung |
| `control_signal.json` | `LoveYou Agent` (dari Tray / Remote Command) | `native-host/host.py` | Meneruskan sinyal `pause` / `resume` / `stop` dengan nomor `seq` monoton |
| `host_status_<browser>.json` | `native-host/host.py` (terpisah per browser: `chrome`, `edge`, `firefox`) | `BrowserCaptureService` | Menyimpan status live extension, `permission_mode`, `local_session_state`, `active_rule_id`, `matched_domain`, `config_version`, `captures_sent`, `last_error`, `updated_at` |
| `spool/incoming/` | `native-host/image_assembler.py` | `BrowserCaptureService` | Menampung file gambar hasil capture tab + `<capture_id>.meta.json` siap masuk ke `SyncService` |

---

## 6. Kontrak Metadata `SyncService` & Tabel `hasil_ss`

Setiap file dari `BrowserCaptureService` masuk ke `SyncService.enqueue(item)` dengan field metadata lengkap:

```json
{
  "source": "browser_tab",
  "browser": "chrome",
  "rule_id": "konstanta-domain",
  "device_id": "uuid-device",
  "origin_domain": "www.konstantaedu.com",
  "captured_at": "2026-11-23T13:05:10Z",
  "mime_type": "image/webp",
  "image_checksum": "sha256-hex"
}
```

- **Penamaan file & storage:**
  - `browser_tab`: `browser_<browser>_<HH-MM-SS>_<DD-MM-YYYY>_<Hari>.<ext>` (contoh: `browser_chrome_13-05-10_23-11-2026_Senin.webp`).
  - `application_window`: `window_<HH-MM-SS>_<DD-MM-YYYY>_<Hari>.<ext>`.
  - `desktop_mss`: `ss_<HH-MM-SS>_<DD-MM-YYYY>_<Hari>.<ext>` *(tetap 100% sama dengan format eksisting)*.
- **Strategi Insert Supabase `hasil_ss` (Graceful Fallback):**
  1. Kolom `active_window` diisi `[chrome] www.konstantaedu.com` (untuk `browser_tab`).
  2. Kolom `notes` selalu menyertakan metadata terstruktur: `[source=browser_tab | browser=chrome | rule=konstanta-domain | domain=www.konstantaedu.com | sha256=<16-hex>]`.
  3. `SupabaseLogger.log_record()` mencoba insert dengan kolom `user_name` + metadata opsional; jika tabel Supabase belum memiliki kolom tambahan, otomatis fallback ke skema kolom standar yang ada tanpa gagal.

---

## 7. Matriks Kompatibilitas Browser (Chrome, Edge, Firefox)

| Fitur / Aspek | Google Chrome (MV3) | Microsoft Edge (MV3) | Mozilla Firefox (MV3 Gecko) |
| :--- | :--- | :--- | :--- |
| **Paket Build** | `browser-extension/dist/chromium/` | `browser-extension/dist/chromium/` *(shared Chromium build)* | `browser-extension/dist/firefox/` |
| **Manifest Background** | `"background": { "service_worker": "background.js", "type": "module" }` | Sama dengan Chrome | `"background": { "scripts": ["background.js"], "type": "module" }` + `"browser_specific_settings": { "gecko": { "id": "loveyou-capture@xoose.local", "strict_min_version": "121.0" } }` |
| **Namespace API** | `chrome.*` via `shared/browser-api.js` (Promise wrapper) | `chrome.*` via `shared/browser-api.js` | `browser.*` native Promise via `shared/browser-api.js` |
| **Scheduler Tahan Lifecycle** | `chrome.alarms` (min period di unpacked/MV3 + wakeup timer fallback untuk interval < 60 detik saat sesi aktif) | Sama dengan Chrome | `browser.alarms` + wakeup timer saat sesi aktif |
| **`tabs.captureVisibleTab()`** | Format native `png`/`jpeg`; konversi WEBP di `OffscreenCanvas` atau host `Pillow` | Sama dengan Chrome | Format native `png`/`jpeg`; konversi WEBP di host `Pillow` (fallback `png`) |
| **Izin Local-Start (Default)** | `"permissions": ["activeTab", "tabs", "alarms", "storage", "nativeMessaging"]` | Sama dengan Chrome | `"permissions": ["activeTab", "tabs", "alarms", "storage", "nativeMessaging"]` |
| **Izin Automatic Domain Mode** | `"optional_host_permissions": ["<all_urls>"]` (diminta eksplisit lewat aksi klik user di popup) | Sama dengan Chrome | `"optional_permissions": ["<all_urls>"]` / `"optional_host_permissions": ["<all_urls>"]` |
| **Native Host Registry Key** | `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.xoose.loveyou.host` | `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.xoose.loveyou.host` | `HKCU\Software\Mozilla\NativeMessagingHosts\com.xoose.loveyou.host` |
| **Host Manifest Allowlist Key** | `"allowed_origins": ["chrome-extension://<CHROME_EXTENSION_ID>/"]` | `"allowed_origins": ["chrome-extension://<EDGE_EXTENSION_ID>/"]` | `"allowed_extensions": ["loveyou-capture@xoose.local"]` |
| **Catatan Khusus `alarms` Interval < 30 detik** | Chrome MV3 `alarms.create({ periodInMinutes })` dibatasi min ~30 detik di rilis terbaru; saat sesi capture aktif & `connectNative` port terbuka, Port Native Messaging menjaga SW tetap hidup sehingga timer presisi + alarm watchdog (0.5 menit) bekerja bersamaan secara andal | Sama dengan Chrome | Firefox event page / background script aktif selama port Native Messaging terbuka + alarm watchdog |
