# Matriks Izin Browser, Transparansi & Desain Indikator Minimalis

**Milestone:** BC-1 — Desain & Schema  
**Tanggal:** 23 November 2026  
**Dokumen Arsitektur:** [browser-capture-architecture.md](file:///D:/KULIAH/KODINGAN/xoose-loveyou/docs/browser-capture-architecture.md)

---

## 1. Prinsip Transparansi & Keamanan Izin

1. **Opt-In & Default Aman:** Konfigurasi awal `browser_capture.enabled` selalu `false`. Extension tidak menangkap apapun sebelum aturan diaktifkan oleh admin **dan** izin/sesi lokal disetujui oleh pengguna browser.
2. **Tanpa Bypass Izin:** Extension tidak pernah menyamarkan dialog persetujuan browser, tidak pernah mengakses tab latar belakang, dan tidak pernah membuka HTTP server lokal pada port jaringan.
3. **Kontrol Lokal Selalu Menang:** Pengguna perangkat kapan saja dapat menekan tombol **Pause** atau **Stop** lokal dari popup Extension maupun dari menu klik-kanan System Tray LoveYou. Sinyal stop lokal menghentikan capture segera dan dilaporkan ke Xoose.
4. **Minimalis & Tidak Mengganggu (Sesuai Keputusan #7):** Indikator aktif, badge ikon extension, popup status, dan menu System Tray dibuat ringkas, tenang, dan minimalis—tanpa banner/overlay mengambang pada halaman web target.

---

## 2. Matriks Mode Izin Browser

| Aspek | Mode 1: `local_start` *(Default)* | Mode 2: `automatic_domain` *(Opsional)* |
| :--- | :--- | :--- |
| **Izin Manifest Wajib** | `activeTab`, `tabs`, `alarms`, `storage`, `nativeMessaging` | Sama + **`optional_host_permissions`: `["<all_urls>"]`** |
| **Cara Aktivasi** | Pengguna membuka popup Extension pada tab target dan menekan tombol **Start** (tindakan klik eksplisit mengaktifkan `activeTab`). | Pengguna menekan tombol **Izinkan Mode Otomatis** pada popup Extension; browser menampilkan prompt resmi izin akses situs (`<all_urls>`). |
| **Lingkup Capture** | Hanya tab aktif yang sedang diberi izin `activeTab` dan cocok dengan rule domain. | Tab aktif manapun yang cocok dengan daftar rule domain dari Xoose (secara otomatis saat berpindah ke domain yang cocok). |
| **Saat Pindah Origin / Domain** | Akses `activeTab` berakhir otomatis oleh browser dan capture langsung dijeda (`paused_origin_changed`). | Jika domain baru tidak ada di daftar rule → capture langsung dijeda (`idle_mismatch`). Jika cocok → capture berjalan kembali. |
| **Saat Browser Tidak Fokus** | Capture otomatis dijeda (`paused_unfocused`) jika `pause_when_browser_unfocused: true`. | Sama — otomatis dijeda (`paused_unfocused`). |
| **Saat Tab Tidak Aktif** | Capture hanya berjalan pada tab aktif (`tabs.captureVisibleTab()`). Tab background tidak pernah diambil. | Sama — hanya isi tab aktif yang terlihat. |
| **Saat Izin Dicabut Pengguna** | Capture langsung berhenti (`stopped_permission_revoked`) dan status dikirim ke Xoose. | Listener `permissions.onRemoved` langsung menghentikan capture (`stopped_permission_revoked`) dan kembali ke `local_start`. |
| **Kebutuhan Rebuild saat Admin Ubah Domain** | **Tidak perlu.** Rule baru dikirim live via Agent → Native Host → Extension. | **Tidak perlu.** Rule baru langsung berlaku pada tab yang cocok. |

### Perbedaan API Izin per Browser

| Browser | Request Izin Opsional `<all_urls>` | Cek Status Izin | Revoke / Hapus Izin |
| :--- | :--- | :--- | :--- |
| **Google Chrome** | `chrome.permissions.request({ origins: ["<all_urls>"] })` *(harus di dalam user gesture click popup)* | `chrome.permissions.contains({ origins: ["<all_urls>"] })` | `chrome.permissions.remove({ origins: ["<all_urls>"] })` atau lewat `chrome://extensions` |
| **Microsoft Edge** | Identik dengan Chrome MV3 | Identik dengan Chrome MV3 | Identik dengan Chrome MV3 (`edge://extensions`) |
| **Mozilla Firefox** | `browser.permissions.request({ origins: ["<all_urls>"] })` *(harus di dalam user gesture click popup)* | `browser.permissions.contains({ origins: ["<all_urls>"] })` | `browser.permissions.remove({ origins: ["<all_urls>"] })` atau lewat `about:addons` |

---

## 3. Desain Indikator Visual & Kontrol Lokal Minimalis

Untuk memenuhi persyaratan transparansi sekaligus menjaga tampilan tetap bersih dan minimalis seperti desain Xoose/LoveYou lainnya:

### 3.1 Badge Ikon Toolbar Extension (Minimalis, Tanpa Overlay Halaman)
- **Tidak ada** injeksi DOM / kotak merah / overlay melayang pada halaman web yang dikunjungi.
- Indikator cukup berupa **badge mikro** di pojok ikon toolbar Extension:

| State Capture | Teks Badge | Warna Latar Badge | Makna |
| :--- | :---: | :---: | :--- |
| **Capturing (Aktif)** | `•` atau `ON` | `#10B981` *(Emerald halus)* | Tab aktif cocok dengan domain rule & sedang menangkap layar |
| **Paused (Dijeda)** | `II` | `#F59E0B` *(Amber lembut)* | Dijeda lokal oleh user, browser unfocused, atau pindah domain |
| **Error / Host Disconnected** | `!` | `#EF4444` *(Rose lembut)* | Native Host terputus atau izin dicabut |
| **Idle / Stopped / Disabled** | *(kosong)* | *(transparan)* | Tidak sedang menangkap layar |

### 3.2 Popup Extension Minimalis (`popup.html` — Lebar `280px`)
Mengikuti bahasa visual Xoose (`#FAFAFB` background, `#FFFFFF` card, `#1A1D1F` teks utama, border `#E5E7EB`, radius `12px`):
- **Header Ringkas:** Nama aplikasi + 1 titik indikator warna status (`Aktif`, `Jeda`, `Siap`, `Berhenti`).
- **Baris Info Ringkas (3 baris padat):**
  - *Mode:* `Local-Start` / `Otomatis` (serta versi config mis. `v3`).
  - *Domain:* Domain aktif yang cocok (mis. `konstantaedu.com`) atau `Tidak cocok`.
  - *Koneksi:* `Host terhubung` / `Terputus`.
- **Kontrol Lokal Minimalis (1 baris tombol):**
  - Tombol **`Mulai` / `Jeda`** *(toggle tunggal)*
  - Tombol **`Hentikan`** *(Stop lokal)*
- **Footer Opsional Ringkas:** Tautan/toggle kecil untuk meminta atau mencabut izin mode otomatis (`<all_urls>`), hanya muncul saat dibutuhkan.

### 3.3 System Tray LoveYou (Tetap Minimalis)
- Hover tooltip ikon System Tray **tetap kosong (`" "`)** sesuai preferensi minimalis eksisting.
- Pada menu klik-kanan System Tray, pengguna tetap memiliki kontrol lokal **Jeda / Lanjutkan** dan **Hentikan** yang otomatis mengirimkan sinyal `control_signal.json` ke Native Host sehingga sinkron antara Tray dan Extension.

---

## 4. Matriks Skenario Keamanan & Kegagalan Izin

| Kejadian | Aksi Wajib Extension & Agent | Laporan Status ke Xoose |
| :--- | :--- | :--- |
| Pengguna klik **Pause** di popup atau Tray | Hentikan alarm/capture segera; tetap simpan koneksi host | `current_status: "Paused"`, `details.local_session_state: "paused"` |
| Pengguna klik **Stop** di popup atau Tray | Hentikan sesi lokal & batalkan chunk berjalan (`capture_abort`) | `current_status: "Stopped"`, `details.local_session_state: "stopped"` |
| Browser kehilangan fokus (`WINDOW_ID_NONE`) | Jeda capture selama unfocused | `details.capture_state: "paused_unfocused"` |
| Tab berpindah ke domain non-rule | Jeda capture; bersihkan badge menjadi idle/standby | `details.capture_state: "idle_mismatch"`, `details.matched_domain: null` |
| Pengguna membuka `chrome://`, `edge://`, `about:`, `file://` | Tolak di `domain-matcher.js`; jangan panggil `captureVisibleTab()` | `details.capture_state: "idle_internal_url"` |
| Native Host terputus / crash | Hentikan capture, jadwalkan reconnect dengan backoff (maks 30 dtk), tampilkan badge `!` | Agent mendeteksi stale `host_status_<browser>.json` (> 90 dtk) → `extension_connected: false` |
| Admin ubah `active_source` menjadi `disabled` atau hapus rule | Host push `config_update` → Extension langsung stop capture & bersihkan badge | `details.config_version` diperbarui & dilaporkan ke `/api/v1/agent/status` |
