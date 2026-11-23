# Xoose–LoveYou Native Messaging Host (`com.xoose.loveyou.host`)

Jembatan lokal resmi WebExtensions Native Messaging (`stdin`/`stdout` 32-bit length-prefixed JSON) antara Browser Extension (Chrome, Edge, Firefox) dan LoveYou Desktop Agent tanpa membuka port HTTP lokal.

## Komponen

- `protocol.py` — Framing 32-bit little-endian JSON, validasi allowlist tipe pesan, dan penolakan field terlarang (`shell`, `exec`, `output_path`, dll.).
- `image_assembler.py` — Penyusun chunk Base64, verifikasi UUID, urutan, anti-duplikasi, timeout 30 detik, verifikasi SHA-256, konversi WEBP (fallback PNG), dan penulisan atomik ke `spool/incoming/`.
- `host.py` — Entry point Native Messaging Host (`stdout` 100% bersih untuk protokol; log hanya ke `stderr` & file log).
- `host_manifest/` — Template manifest untuk Chrome (`allowed_origins`), Edge (`allowed_origins`), dan Firefox (`allowed_extensions`).
- `install/` — `install-host.ps1` & `uninstall-host.ps1` berbasis Registry `HKCU` (per-user).

## Cara Pengujian

```powershell
cd "D:\KULIAH\KODINGAN\xoose-loveyou\native-host"
python -m pytest -v
```

## Registrasi HKCU (Berparameter Extension ID)

```powershell
# Setelah memuat extension di chrome://extensions atau edge://extensions, salin Extension ID aktual:
powershell -ExecutionPolicy Bypass -File ".\install\install-host.ps1" `
  -ChromeExtensionId "<32-char-chrome-extension-id>" `
  -EdgeExtensionId "<32-char-edge-extension-id>" `
  -FirefoxAddonId "loveyou-capture@xoose.local"

# Uninstall bersih:
powershell -ExecutionPolicy Bypass -File ".\install\uninstall-host.ps1"
```
