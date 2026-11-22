# Xoose Builder Engine

Python Build Engine yang menghubungkan Laravel Xoose dengan template aplikasi LoveYou berbasis Windows executable (`.exe`).

## Struktur Paket
- `src/xoose_builder/`:
  - `cli.py`: Antarmuka CLI (`validate`, `workspace`, `build`)
  - `manifest.py`: Validasi schema manifest JSON
  - `workspace.py`: Pengelolaan salinan kerja proyek yang terisolasi
  - `exceptions.py`: Definisi exception keamanan dan runtime
- `tests/`: Unit test untuk validasi slug, path traversal, dan isolasi workspace.

## Cara Penggunaan CLI
```powershell
# Validasi manifest
python -m xoose_builder.cli validate --manifest "path/to/manifest.json"

# Buat workspace proyek baru
python -m xoose_builder.cli workspace --manifest "path/to/manifest.json" --workspace-root "D:/KULIAH/KODINGAN/xoose-loveyou/workspace"

# Build executable (PyInstaller)
python -m xoose_builder.cli build --manifest "path/to/manifest.json" --workspace-root "D:/KULIAH/KODINGAN/xoose-loveyou/workspace" --output-dir "D:/KULIAH/KODINGAN/xoose-loveyou/builds"
```
