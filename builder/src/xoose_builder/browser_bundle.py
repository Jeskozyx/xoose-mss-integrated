"""
BrowserCaptureBundler: Perluasan xoose_builder (Milestone BC-6) untuk membundel:
1. Browser Extension variant Chromium (Chrome & Edge) dan Firefox (+ ZIP)
2. Native Messaging Host Python yang dikompilasi PyInstaller (--onedir, stdio-safe)
3. Template host manifest Chrome/Edge/Firefox & script install/uninstall HKCU Windows
4. bundle-manifest.json ber-checksum SHA-256 (nol secret/token perangkat di dalam paket)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xoose_builder.builder import sanitize_log_line
from xoose_builder.exceptions import BuilderError
from xoose_builder.manifest import assert_no_forbidden_secrets
from xoose_builder.signer import compute_sha256


def _zip_directory(source_dir: Path, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.relative_to(source_dir).as_posix())
    return zip_path


class BrowserCaptureBundler:
    """Membundel Browser Extension (Chromium & Firefox) + Native Messaging Host (PyInstaller onedir)."""

    def __init__(
        self,
        integration_root: str | Path,
        output_dir: str | Path,
        logs_dir: str | Path,
    ):
        self.integration_root = Path(integration_root).resolve()
        self.extension_src_dir = self.integration_root / "browser-extension"
        self.native_host_src_dir = self.integration_root / "native-host"
        self.output_dir = Path(output_dir).resolve()
        self.logs_dir = Path(logs_dir).resolve()

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _validate_sources(self) -> None:
        required_paths = [
            self.extension_src_dir / "shared" / "domain-matcher.js",
            self.extension_src_dir / "shared" / "capture-controller.js",
            self.extension_src_dir / "chromium" / "manifest.json",
            self.extension_src_dir / "firefox" / "manifest.json",
            self.native_host_src_dir / "host.py",
            self.native_host_src_dir / "protocol.py",
            self.native_host_src_dir / "image_assembler.py",
            self.native_host_src_dir / "host_manifest" / "chrome.template.json",
            self.native_host_src_dir / "host_manifest" / "edge.template.json",
            self.native_host_src_dir / "host_manifest" / "firefox.template.json",
            self.native_host_src_dir / "install" / "install-host.ps1",
            self.native_host_src_dir / "install" / "uninstall-host.ps1",
        ]
        for req in required_paths:
            if not req.exists():
                raise BuilderError(
                    f"File sumber browser-capture wajib tidak ditemukan: {req}",
                    code="BROWSER_CAPTURE_SOURCE_MISSING",
                )

        # Audit rahasia sebelum membundel manifest/template
        for json_file in (
            self.extension_src_dir / "chromium" / "manifest.json",
            self.extension_src_dir / "firefox" / "manifest.json",
            self.native_host_src_dir / "host_manifest" / "chrome.template.json",
            self.native_host_src_dir / "host_manifest" / "edge.template.json",
            self.native_host_src_dir / "host_manifest" / "firefox.template.json",
        ):
            assert_no_forbidden_secrets(json_file.read_text(encoding="utf-8"), path=str(json_file.name))

    def _stage_extensions(self, bundle_dir: Path) -> dict[str, dict[str, str]]:
        ext_root = bundle_dir / "extensions"
        shared_dir = self.extension_src_dir / "shared"
        results: dict[str, dict[str, str]] = {}

        for variant in ("chromium", "firefox"):
            dst = ext_root / variant
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(self.extension_src_dir / variant, dst)
            shutil.copytree(shared_dir, dst / "shared")

            zip_file = _zip_directory(dst, ext_root / f"xoose-capture-{variant}.zip")
            results[variant] = {
                "dir": str(dst).replace("\\", "/"),
                "zip": str(zip_file).replace("\\", "/"),
                "zip_sha256": compute_sha256(zip_file),
            }

        return results

    def _build_native_host_onedir(self, bundle_dir: Path, bundle_id: str, skip_pyinstaller: bool = False) -> dict[str, Any]:
        host_bundle_dir = bundle_dir / "native-host"
        host_bundle_dir.mkdir(parents=True, exist_ok=True)

        # Salin manifest templates & install/uninstall PowerShell scripts
        shutil.copytree(
            self.native_host_src_dir / "host_manifest",
            host_bundle_dir / "host_manifest",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            self.native_host_src_dir / "install",
            host_bundle_dir / "install",
            dirs_exist_ok=True,
        )

        if skip_pyinstaller:
            for py_file in ("host.py", "protocol.py", "image_assembler.py"):
                shutil.copy2(self.native_host_src_dir / py_file, host_bundle_dir / py_file)
            return {
                "mode": "python_script",
                "executable": str(host_bundle_dir / "host.py").replace("\\", "/"),
                "sha256_checksum": compute_sha256(host_bundle_dir / "host.py"),
                "log_path": None,
            }

        dist_dir = host_bundle_dir / "dist"
        work_dir = host_bundle_dir / "work"
        spec_dir = host_bundle_dir
        dist_dir.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)

        log_path = self.logs_dir / f"native_host_build_{bundle_id}.log"
        entry_py = self.native_host_src_dir / "host.py"

        # WAJIB --onedir + --console agar stdin/stdout pipe Native Messaging tetap aktif di Windows!
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--name=xoose-native-host",
            "--onedir",
            "--console",
            "--noconfirm",
            "--clean",
            f"--paths={self.native_host_src_dir}",
            f"--distpath={dist_dir}",
            f"--workpath={work_dir}",
            f"--specpath={spec_dir}",
            "--hidden-import=protocol",
            "--hidden-import=image_assembler",
            "--hidden-import=PIL",
            "--hidden-import=PIL._webp",
            "--collect-all=PIL",
            str(entry_py),
        ]

        with open(log_path, "w", encoding="utf-8") as log_f:
            log_f.write(f"=== NATIVE HOST ONEDIR BUILD ({bundle_id}) ===\n")
            log_f.write(f"Command: {' '.join(cmd)}\n\n")
            log_f.flush()

            proc = subprocess.Popen(
                cmd,
                cwd=str(self.native_host_src_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                log_f.write(sanitize_log_line(line))
                log_f.flush()
            proc.wait()
            exit_code = proc.returncode
            log_f.write(f"\n=== EXIT CODE {exit_code} ===\n")

        expected_exe = dist_dir / "xoose-native-host" / "xoose-native-host.exe"
        if exit_code != 0 or not expected_exe.exists():
            raise BuilderError(
                f"PyInstaller build native-host gagal (exit={exit_code}). Log: {log_path}",
                code="NATIVE_HOST_BUILD_FAILED",
            )

        # Bersihkan folder work sementara agar paket distribusi tetap ringkas
        shutil.rmtree(work_dir, ignore_errors=True)
        spec_file = spec_dir / "xoose-native-host.spec"
        if spec_file.exists():
            spec_file.unlink(missing_ok=True)

        return {
            "mode": "pyinstaller_onedir",
            "executable": str(expected_exe).replace("\\", "/"),
            "executable_dir": str(expected_exe.parent).replace("\\", "/"),
            "sha256_checksum": compute_sha256(expected_exe),
            "log_path": str(log_path).replace("\\", "/"),
        }

    def bundle(self, bundle_id: str = "latest", skip_pyinstaller: bool = False) -> dict[str, Any]:
        """Menghasilkan paket distribusi lengkap Extension Chromium/Firefox + Native Host + Installer."""
        self._validate_sources()

        safe_id = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in (bundle_id or "latest")).strip("_") or "latest"
        bundle_dir = self.output_dir / "browser-capture" / f"bundle_{safe_id}"
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        bundle_dir.mkdir(parents=True, exist_ok=True)

        extensions_info = self._stage_extensions(bundle_dir)
        native_host_info = self._build_native_host_onedir(bundle_dir, safe_id, skip_pyinstaller=skip_pyinstaller)

        manifest_summary = {
            "success": True,
            "bundle_id": safe_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "bundle_dir": str(bundle_dir).replace("\\", "/"),
            "extensions": extensions_info,
            "native_host": native_host_info,
            "install_script": str(bundle_dir / "native-host" / "install" / "install-host.ps1").replace("\\", "/"),
            "uninstall_script": str(bundle_dir / "native-host" / "install" / "uninstall-host.ps1").replace("\\", "/"),
        }

        (bundle_dir / "bundle-manifest.json").write_text(
            json.dumps(manifest_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return manifest_summary
