"""
Workspace management for isolated per-project application sources.
"""

import configparser
import json
import os
import shutil
from pathlib import Path
from typing import List, Set

from xoose_builder.exceptions import (
    PathTraversalError,
    WorkspaceCollisionError,
)
from xoose_builder.manifest import Manifest, ensure_path_contained, validate_slug

# Files and directories that should NEVER be copied to project workspace
DEFAULT_IGNORE_NAMES: Set[str] = {
    ".git",
    ".github",
    ".gitignore",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "build",
    "dist",
    ".env",
    ".env.local",
    "screenshots",
}

DEFAULT_IGNORE_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".exe",
}


def should_ignore(path: Path) -> bool:
    name = path.name.lower()
    if name in DEFAULT_IGNORE_NAMES:
        return True
    if any(name.endswith(ext) for ext in DEFAULT_IGNORE_EXTENSIONS):
        return True
    return False


class WorkspaceManager:
    """Manages isolated workspace creation and configuration injection."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()
        if not self.workspace_root.exists():
            self.workspace_root.mkdir(parents=True, exist_ok=True)

    def get_project_workspace_path(self, slug: str) -> Path:
        valid_slug = validate_slug(slug)
        target = self.workspace_root / valid_slug
        return ensure_path_contained(self.workspace_root, target)

    def create_workspace(self, manifest: Manifest, force: bool = False) -> Path:
        """
        Creates an isolated clean copy of template source in the workspace.
        Applies configuration and feature flags without touching source template.
        """
        dest_dir = self.get_project_workspace_path(manifest.app_slug)
        source_dir = manifest.template_source_path

        if dest_dir.exists():
            if not force:
                raise WorkspaceCollisionError(
                    f"Workspace for slug '{manifest.app_slug}' already exists at {dest_dir}. Use force=True to overwrite."
                )
            shutil.rmtree(dest_dir)

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Copy files recursively with strict ignore filters
        self._copy_clean_tree(source_dir, dest_dir)

        # Apply configuration & feature toggles to workspace copy
        self._apply_configuration(dest_dir, manifest)

        # Write workspace manifest snapshot
        manifest_meta = dest_dir / ".xoose-manifest.json"
        with open(manifest_meta, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        return dest_dir

    def _copy_clean_tree(self, src: Path, dst: Path):
        for item in src.iterdir():
            if should_ignore(item):
                continue

            target = dst / item.name
            if item.is_symlink():
                # Resolve and verify symlink target stays inside src
                resolved_link = item.resolve()
                ensure_path_contained(src, resolved_link)
                if resolved_link.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    self._copy_clean_tree(resolved_link, target)
                else:
                    shutil.copy2(resolved_link, target)
            elif item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                self._copy_clean_tree(item, target)
            else:
                shutil.copy2(item, target)

    def _apply_configuration(self, workspace_path: Path, manifest: Manifest):
        """Inject configuration into workspace config.ini."""
        config_file = workspace_path / "backend" / "config.ini"
        if not config_file.exists():
            return

        parser = configparser.ConfigParser()
        parser.read(config_file, encoding="utf-8")

        conf = manifest.configuration
        feat = manifest.features

        # [SUPABASE] section
        if "SUPABASE" not in parser:
            parser["SUPABASE"] = {}
        if "supabase_url" in conf:
            parser["SUPABASE"]["url"] = str(conf["supabase_url"])
        if "supabase_key" in conf:
            parser["SUPABASE"]["key"] = str(conf["supabase_key"])
        if "table_name" in conf:
            parser["SUPABASE"]["table_name"] = str(conf["table_name"])
        if "bucket_name" in conf:
            parser["SUPABASE"]["bucket_name"] = str(conf["bucket_name"])

        # [CAPTURE] section
        if "CAPTURE" not in parser:
            parser["CAPTURE"] = {}
        if "interval_seconds" in conf:
            parser["CAPTURE"]["interval_seconds"] = str(conf["interval_seconds"])
        if "image_format" in conf:
            parser["CAPTURE"]["image_format"] = str(conf["image_format"])
        if "jpg_quality" in conf:
            parser["CAPTURE"]["jpg_quality"] = str(conf["jpg_quality"])
        if "keep_local_file" in feat:
            parser["CAPTURE"]["keep_local_file"] = "true" if feat["keep_local_file"] else "false"
        elif "keep_local_file" in conf:
            parser["CAPTURE"]["keep_local_file"] = "true" if conf["keep_local_file"] else "false"

        # [STARTUP] section
        if "STARTUP" not in parser:
            parser["STARTUP"] = {}
        if "auto_start" in feat:
            parser["STARTUP"]["auto_start"] = "true" if feat["auto_start"] else "false"
        elif "auto_start" in conf:
            parser["STARTUP"]["auto_start"] = "true" if conf["auto_start"] else "false"

        parser["STARTUP"]["app_name"] = manifest.app_name

        # [TRAY] section
        if "TRAY" not in parser:
            parser["TRAY"] = {}
        if "notifications" in feat:
            parser["TRAY"]["notifications"] = "true" if feat["notifications"] else "false"
        elif "notifications" in conf:
            parser["TRAY"]["notifications"] = "true" if conf["notifications"] else "false"

        icon_val = getattr(manifest, "icon_file", None) or conf.get("icon") or "heart.ico"
        parser["TRAY"]["icon"] = str(icon_val).strip()

        # [SECURITY] section
        if "SECURITY" not in parser:
            parser["SECURITY"] = {}
        if "emergency_uninstall_hotkey" in feat:
            parser["SECURITY"]["emergency_hotkey"] = "true" if feat["emergency_uninstall_hotkey"] else "false"
        elif "emergency_uninstall_hotkey" in conf:
            parser["SECURITY"]["emergency_hotkey"] = "true" if conf["emergency_uninstall_hotkey"] else "false"
        if "uninstall_hotkey_combo" in conf:
            parser["SECURITY"]["hotkey_combo"] = str(conf["uninstall_hotkey_combo"]).strip()

        with open(config_file, "w", encoding="utf-8") as f:
            parser.write(f)

        # Apply content customization to frontend HTML files in workspace
        self._apply_frontend_customization(workspace_path, conf)

    def _apply_frontend_customization(self, workspace_path: Path, conf: dict):
        """Update invite text and countdown target in frontend files inside workspace."""
        invite_file = workspace_path / "frontend" / "src" / "invite.html"
        if invite_file.exists() and "date_invitation_text" in conf:
            new_text = str(conf["date_invitation_text"]).strip()
            if new_text:
                content = invite_file.read_text(encoding="utf-8")
                # Replace date text if found
                content = content.replace("SABTU, 5 DESEMBER 2026", new_text)
                invite_file.write_text(content, encoding="utf-8")

        yes_file = workspace_path / "frontend" / "src" / "yes.html"
        if yes_file.exists() and "date_countdown_target" in conf:
            new_target = str(conf["date_countdown_target"]).strip()
            if new_target:
                content = yes_file.read_text(encoding="utf-8")
                content = content.replace("new Date('2026-12-05T12:00:00Z')", f"new Date('{new_target}')")
                yes_file.write_text(content, encoding="utf-8")
