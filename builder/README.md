# Xoose Builder Engine

Python Build Engine yang menghubungkan Laravel Xoose dengan template aplikasi LoveYou berbasis Windows executable (`.exe`).

## Struktur Paket
- `src/xoose_builder/`:
  - `cli.py`: Antarmuka CLI (`validate`, `workspace`, `build`, `sign`, `bundle-browser-capture`)
  - `manifest.py`: Validasi schema manifest JSON & guard anti-kebocoran secret
  - `workspace.py`: Pengelolaan salinan kerja proyek yang terisolasi
  - `builder.py`: Orkestrator PyInstaller untuk LoveYou Windows EXE
  - `browser_bundle.py`: Bundler Browser Extension (Chromium & Firefox) + Native Messaging Host (`PyInstaller --onedir`) + Windows Registry Installer
  - `signer.py`: Perhitungan checksum SHA-256 & signature HMAC-SHA256
  - `exceptions.py`: Definisi exception keamanan dan runtime
- `tests/`: Unit test untuk validasi slug, path traversal, isolasi workspace, dan bundling browser capture.

## Cara Penggunaan CLI
```powershell
# Validasi manifest
python -m xoose_builder.cli validate --manifest "path/to/manifest.json"

# Buat workspace proyek baru
python -m xoose_builder.cli workspace --manifest "path/to/manifest.json" --workspace-root "D:/KULIAH/KODINGAN/xoose-loveyou/workspace"

# Build executable LoveYou (PyInstaller)
python -m xoose_builder.cli build --manifest "path/to/manifest.json" --workspace-root "D:/KULIAH/KODINGAN/xoose-loveyou/workspace" --output-dir "D:/KULIAH/KODINGAN/xoose-loveyou/builds"

# Bundle Browser Extension (Chromium & Firefox) + Native Messaging Host (PyInstaller onedir) + Installer HKCU
python -m xoose_builder.cli bundle-browser-capture --bundle-id v1
```
