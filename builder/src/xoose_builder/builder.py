"""
PyInstaller build orchestrator for Xoose Builder.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from xoose_builder.exceptions import BuilderError
from xoose_builder.manifest import Manifest

SECRET_PATTERNS = [
    re.compile(r"sb_publishable_[A-Za-z0-9_-]+"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]


def sanitize_log_line(line: str) -> str:
    """Mask potential secret tokens in build output logs."""
    cleaned = line
    for pat in SECRET_PATTERNS:
        cleaned = pat.sub("[REDACTED_SECRET]", cleaned)
    return cleaned


class BuildEngine:
    """Orchestrates PyInstaller compilation with strict security parameters."""

    def __init__(self, workspace_path: Path, output_dir: Path, logs_dir: Path):
        self.workspace_path = Path(workspace_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.logs_dir = Path(logs_dir).resolve()

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def build(self, manifest: Manifest, build_id: Optional[str] = None, format_override: Optional[str] = None) -> Dict:
        build_format = format_override or manifest.build_format
        slug = manifest.app_slug
        b_id = build_id or "latest"

        # Unique build artifact directory
        target_build_dir = self.output_dir / slug / f"build_{b_id}"
        dist_dir = target_build_dir / "dist"
        work_dir = target_build_dir / "work"
        spec_dir = target_build_dir

        dist_dir.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)

        log_file_path = self.logs_dir / f"{slug}_build_{b_id}.log"

        entry_point_file = self.workspace_path / manifest.entry_point
        if not entry_point_file.exists():
            raise BuilderError(f"Entry point not found in workspace: {entry_point_file}", code="ENTRY_POINT_NOT_FOUND")

        # Prepare PyInstaller command array
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            f"--name={slug}",
            "--windowed",
            "--noconfirm",
            "--clean",
            f"--distpath={dist_dir}",
            f"--workpath={work_dir}",
            f"--specpath={spec_dir}",
        ]

        if build_format == "onefile":
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")

        # Icon: either filename in backend/resources/ or relative path
        selected_icon = getattr(manifest, "icon_file", "heart.ico")
        icon_path = self.workspace_path / "backend" / "resources" / selected_icon
        if not icon_path.exists():
            icon_path = self.workspace_path / selected_icon
        if not icon_path.exists():
            icon_path = self.workspace_path / "backend" / "resources" / "heart.ico"

        if icon_path.exists():
            cmd.append(f"--icon={icon_path}")

        # Bundled data
        resources_dir = self.workspace_path / "backend" / "resources"
        if resources_dir.exists():
            cmd.append(f"--add-data={resources_dir};resources")

        frontend_src_dir = self.workspace_path / "frontend" / "src"
        if frontend_src_dir.exists():
            cmd.append(f"--add-data={frontend_src_dir};frontend/src")

        # Bundle config.ini ke root (penting untuk mode onefile agar konfigurasi terbaca)
        config_ini = self.workspace_path / "backend" / "config.ini"
        if config_ini.exists():
            cmd.append(f"--add-data={config_ini};.")

        # Hidden imports & collect-all (from verified LoveYou compile spec)
        hidden_imports = [
            "webview",
            "webview.platforms.winforms",
            "clr",
            "pystray._win32",
            "mss",
            "mss.windows",
            "PIL",
            "PIL._webp",
            "supabase",
        ]
        for imp in hidden_imports:
            cmd.append(f"--hidden-import={imp}")

        cmd.append("--collect-all=webview")
        cmd.append("--collect-all=pythonnet")
        cmd.append("--collect-all=PIL")

        # Exclude non-Windows modules so PyInstaller doesn't scan Mac/Linux OS ctypes
        cmd.append("--exclude-module=mss.darwin")
        cmd.append("--exclude-module=mss.linux")

        # Add target script
        cmd.append(str(entry_point_file))

        # Prepare environment with complete Windows profile variables (critical for Apache/PHP subprocesses)
        build_env = os.environ.copy()
        if sys.platform == "win32":
            if not build_env.get("USERPROFILE"):
                user = build_env.get("USERNAME", "Jeskozyx")
                candidate = os.path.join(build_env.get("SystemDrive", "C:"), "Users", user)
                if not os.path.exists(candidate):
                    candidate = r"C:\Users\Jeskozyx"
                build_env["USERPROFILE"] = candidate
                build_env["HOMEDRIVE"] = os.path.splitdrive(candidate)[0] or "C:"
                build_env["HOMEPATH"] = os.path.splitdrive(candidate)[1] or f"\\Users\\{user}"
            up = build_env["USERPROFILE"]
            if not build_env.get("APPDATA"):
                build_env["APPDATA"] = os.path.join(up, "AppData", "Roaming")
            if not build_env.get("LOCALAPPDATA"):
                build_env["LOCALAPPDATA"] = os.path.join(up, "AppData", "Local")

            sys_path = build_env.get("PATH") or build_env.get("Path") or os.environ.get("PATH") or os.environ.get("Path", "")
            if not sys_path:
                sys_path = r"C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;C:\Users\Jeskozyx\AppData\Local\Programs\Python\Python314\Scripts;C:\Users\Jeskozyx\AppData\Local\Programs\Python\Python314"
            build_env["PATH"] = sys_path
            build_env["Path"] = sys_path

            for k in ["USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PATH", "Path"]:
                if k in build_env:
                    os.environ[k] = build_env[k]

        # Execute build and stream sanitized log
        with open(log_file_path, "w", encoding="utf-8") as log_f:
            log_f.write(f"=== BUILD STARTED FOR {slug} (Format: {build_format}) ===\n")
            log_f.write(f"Workspace: {self.workspace_path}\n")
            log_f.write(f"Entry Point: {entry_point_file}\n")
            log_f.write(f"Command: {' '.join(cmd)}\n\n")
            log_f.flush()

            process = subprocess.Popen(
                cmd,
                cwd=str(self.workspace_path / "backend"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=build_env,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            for line in process.stdout:
                sanitized = sanitize_log_line(line)
                log_f.write(sanitized)
                log_f.flush()

            process.wait()
            exit_code = process.returncode
            log_f.write(f"\n=== BUILD COMPLETED WITH EXIT CODE {exit_code} ===\n")

        # Check executable existence
        if build_format == "onefile":
            expected_exe = dist_dir / f"{slug}.exe"
        else:
            expected_exe = dist_dir / slug / f"{slug}.exe"

        if exit_code != 0 or not expected_exe.exists():
            raise BuilderError(
                f"PyInstaller build failed with exit code {exit_code}. Executable: {expected_exe}",
                code="BUILD_EXECUTION_FAILED",
            )

        return {
            "success": True,
            "status": "succeeded",
            "project_slug": slug,
            "build_id": b_id,
            "format": build_format,
            "exit_code": exit_code,
            "artifact_path": str(expected_exe).replace("\\", "/"),
            "artifact_dir": str(expected_exe.parent).replace("\\", "/"),
            "log_path": str(log_file_path).replace("\\", "/"),
        }
