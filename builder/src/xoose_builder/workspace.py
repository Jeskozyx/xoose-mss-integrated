"""
Workspace management for isolated per-project application sources.
"""

import configparser
import json
import os
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from xoose_builder.exceptions import (
    PathTraversalError,
    WorkspaceCollisionError,
)
from xoose_builder.manifest import Manifest, assert_no_forbidden_secrets, ensure_path_contained, validate_slug

# Files and directories that should NEVER be copied to project workspace
DEFAULT_IGNORE_NAMES: Set[str] = {
    ".git",
    ".github",
    ".gitignore",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "build",
    "dist",
    "tests",
    ".env",
    ".env.local",
    "screenshots",
    "identity.json",
    "processed_commands.json",
}

DEFAULT_IGNORE_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".exe",
}


DEFAULT_INVITE_TEXT = "SABTU, 5 DESEMBER 2026"
DEFAULT_COUNTDOWN_TARGET = "2026-12-05T12:00:00Z"
DEFAULT_TANGGAL_DATE = "2026-12-05"

ID_MONTHS_TO_NUM = {
    "januari": 1, "jan": 1, "january": 1,
    "februari": 2, "feb": 2, "pebruari": 2, "february": 2,
    "maret": 3, "mar": 3, "march": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "jun": 6, "june": 6,
    "juli": 7, "jul": 7, "july": 7,
    "agustus": 8, "agu": 8, "ags": 8, "aug": 8, "august": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10, "oct": 10, "october": 10,
    "november": 11, "nov": 11, "nopember": 11, "nop": 11,
    "desember": 12, "des": 12, "dec": 12, "december": 12,
}

NUM_TO_ID_MONTH = {
    1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL",
    5: "MEI", 6: "JUNI", 7: "JULI", 8: "AGUSTUS",
    9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER",
}

WEEKDAY_TO_ID = {
    0: "SENIN", 1: "SELASA", 2: "RABU", 3: "KAMIS",
    4: "JUMAT", 5: "SABTU", 6: "MINGGU",
}


def parse_date_from_text(text: str) -> Tuple[Optional[Tuple[int, int, int]], Optional[Tuple[int, int]]]:
    """
    Mengekstrak (year, month, day) dan opsional (hour, minute) dari teks tanggal bebas
    (contoh: 'MINGGU, 27 DESEMBER 2026 • 20.00', '14 Februari 2027', '2026-12-25', '25/12/2026').
    """
    if not text:
        return None, None

    cleaned = text.strip()
    lower = cleaned.lower()
    ymd: Optional[Tuple[int, int, int]] = None

    # 1. Pola: DD <Nama Bulan> YYYY
    month_pattern = "|".join(sorted(ID_MONTHS_TO_NUM.keys(), key=len, reverse=True))
    m1 = re.search(rf"\b(\d{{1,2}})\s+({month_pattern})\s+(\d{{4}})\b", lower)
    if m1:
        day, mon_str, year = int(m1.group(1)), m1.group(2), int(m1.group(3))
        month = ID_MONTHS_TO_NUM.get(mon_str, 12)
        try:
            datetime(year, month, day)
            ymd = (year, month, day)
        except ValueError:
            pass

    # 2. Pola: YYYY-MM-DD atau YYYY/MM/DD
    if not ymd:
        m2 = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", lower)
        if m2:
            year, month, day = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            try:
                datetime(year, month, day)
                ymd = (year, month, day)
            except ValueError:
                pass

    # 3. Pola: DD-MM-YYYY atau DD/MM/YYYY
    if not ymd:
        m3 = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", lower)
        if m3:
            day, month, year = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
            try:
                datetime(year, month, day)
                ymd = (year, month, day)
            except ValueError:
                pass

    # Ekstrak jam & menit opsional (cth: '• 19.00', 'pukul 20:30', '19:00')
    hm: Optional[Tuple[int, int]] = None
    # Hapus bagian tanggal terlebih dahulu agar tidak salah mendeteksi angka tanggal sebagai jam
    remainder = lower
    if m1:
        remainder = lower[:m1.start()] + " " + lower[m1.end():]
    tm = re.search(r"(?:•|pukul|jam|\b)\s*([01]?\d|2[0-3])[:\.]([0-5]\d)\b", remainder)
    if tm:
        hm = (int(tm.group(1)), int(tm.group(2)))

    return ymd, hm


def parse_iso_target(iso_str: str) -> Optional[datetime]:
    """Mengurai string ISO 8601 menjadi datetime dalam zona WIB (UTC+7)."""
    if not iso_str:
        return None
    s = iso_str.strip()
    try:
        if s.endswith("Z") or s.endswith("z"):
            dt = datetime.fromisoformat(s[:-1] + "+00:00")
        else:
            dt = datetime.fromisoformat(s)
        wib = timezone(timedelta(hours=7))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=wib)
        return dt.astimezone(wib)
    except Exception:
        return None


def resolve_date_settings(raw_text: str, raw_target: str) -> Dict[str, str]:
    """
    Menyelaraskan date_invitation_text, date_countdown_target, dan tanggal_date (YYYY-MM-DD).
    - Jika user mengubah date_invitation_text (misal 'MINGGU, 27 DESEMBER 2026'), otomatis
      menyesuaikan countdown target & tanggal_date walaupun user tidak mengubah kolom ISO 8601.
    - Jika user mengubah date_countdown_target sementara date_invitation_text masih default,
      otomatis memperbarui date_invitation_text sesuai tanggal tersebut.
    """
    invite_text = (raw_text or "").strip() or DEFAULT_INVITE_TEXT
    target_iso = (raw_target or "").strip() or DEFAULT_COUNTDOWN_TARGET

    parsed_ymd, parsed_hm = parse_date_from_text(invite_text)
    target_dt = parse_iso_target(target_iso)

    wib = timezone(timedelta(hours=7))
    default_ymd = (2026, 12, 5)

    target_ymd = (target_dt.year, target_dt.month, target_dt.day) if target_dt else default_ymd
    target_hm = (target_dt.hour, target_dt.minute) if target_dt else (19, 0)

    if parsed_ymd:
        # User mengkustomisasi teks tanggal, atau teks tanggal memiliki tanggal valid
        if parsed_ymd != default_ymd and target_ymd == default_ymd:
            # User mengubah Teks Tanggal Undangan tetapi membiarkan Target ISO di default -> ikuti Teks Tanggal!
            final_ymd = parsed_ymd
            final_hm = parsed_hm if parsed_hm else target_hm
            dt_wib = datetime(final_ymd[0], final_ymd[1], final_ymd[2], final_hm[0], final_hm[1], 0, tzinfo=wib)
            target_iso = dt_wib.isoformat()
        elif parsed_ymd == default_ymd and target_ymd != default_ymd and invite_text.upper() == DEFAULT_INVITE_TEXT:
            # User hanya mengubah Target ISO sementara Teks Tanggal masih default -> format otomatis Teks Tanggal!
            final_ymd = target_ymd
            dt_obj = datetime(final_ymd[0], final_ymd[1], final_ymd[2])
            day_name = WEEKDAY_TO_ID[dt_obj.weekday()]
            mon_name = NUM_TO_ID_MONTH[final_ymd[1]]
            invite_text = f"{day_name}, {final_ymd[2]} {mon_name} {final_ymd[0]}"
        else:
            # Keduanya diubah: utamakan tanggal dari teks undangan untuk tanggal_date, dan sinkronkan waktu
            final_ymd = parsed_ymd
            if parsed_hm:
                dt_wib = datetime(final_ymd[0], final_ymd[1], final_ymd[2], parsed_hm[0], parsed_hm[1], 0, tzinfo=wib)
                target_iso = dt_wib.isoformat()
            elif target_ymd != parsed_ymd:
                dt_wib = datetime(final_ymd[0], final_ymd[1], final_ymd[2], target_hm[0], target_hm[1], 0, tzinfo=wib)
                target_iso = dt_wib.isoformat()
        tanggal_date = f"{final_ymd[0]:04d}-{final_ymd[1]:02d}-{final_ymd[2]:02d}"
    else:
        # Teks undangan bebas tanpa angka tanggal (misal: 'MALAM MINGGU SPESIAL') -> pakai tanggal dari target_iso
        tanggal_date = f"{target_ymd[0]:04d}-{target_ymd[1]:02d}-{target_ymd[2]:02d}"

    return {
        "date_invitation_text": invite_text,
        "date_countdown_target": target_iso,
        "tanggal_date": tanggal_date,
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

        # [CONTENT] section (Kustomisasi Tanggal Ajakan Date & Countdown)
        resolved_dates = resolve_date_settings(
            str(conf.get("date_invitation_text", "")),
            str(conf.get("date_countdown_target", "")),
        )
        if "CONTENT" not in parser:
            parser["CONTENT"] = {}
        parser["CONTENT"]["date_invitation_text"] = resolved_dates["date_invitation_text"]
        parser["CONTENT"]["date_countdown_target"] = resolved_dates["date_countdown_target"]
        parser["CONTENT"]["tanggal_date"] = resolved_dates["tanggal_date"]

        # [AGENT] section (Identitas proyek per build — TANPA shared device_token atau service_role key)
        if "AGENT" not in parser:
            parser["AGENT"] = {}
        parser["AGENT"]["enabled"] = "true" if manifest.agent_enabled else "false"
        parser["AGENT"]["api_base_url"] = manifest.agent_api_base_url
        parser["AGENT"]["project_slug"] = manifest.agent_project_slug
        parser["AGENT"]["enrollment_code"] = manifest.agent_enrollment_code
        parser["AGENT"]["heartbeat_interval_seconds"] = str(manifest.agent_heartbeat_interval)
        parser["AGENT"]["poll_interval_seconds"] = str(manifest.agent_poll_interval)
        parser["AGENT"]["config_sync_interval_seconds"] = str(manifest.agent_config_sync_interval)
        parser["AGENT"]["realtime_enabled"] = "true" if manifest.agent_realtime_enabled else "false"
        parser["AGENT"]["app_version"] = manifest.agent_app_version

        with open(config_file, "w", encoding="utf-8") as f:
            parser.write(f)

        # Audit akhir isi config.ini yang dihasilkan agar tidak pernah ada secret bocor
        assert_no_forbidden_secrets(config_file.read_text(encoding="utf-8"), path="workspace.config.ini")

        # Apply content customization to frontend HTML files in workspace
        self._apply_frontend_customization(workspace_path, resolved_dates)

    def _apply_frontend_customization(self, workspace_path: Path, resolved_dates: dict):
        """Update invite text, tanggal_date, and countdown target in frontend files inside workspace."""
        new_text = resolved_dates["date_invitation_text"]
        new_target = resolved_dates["date_countdown_target"]
        new_tanggal_date = resolved_dates["tanggal_date"]

        invite_file = workspace_path / "frontend" / "src" / "invite.html"
        if invite_file.exists() and new_text:
            content = invite_file.read_text(encoding="utf-8")
            # 1. Replace span id="inviteDateText" if present
            content = re.sub(
                r'(<span\s+id="inviteDateText">)(.*?)(</span>)',
                lambda m: f"{m.group(1)}{new_text}{m.group(3)}",
                content,
                flags=re.DOTALL,
            )
            # 2. Replace CONFIG_INVITE_TEXT & CONFIG_TANGGAL_DATE in script if present
            content = re.sub(
                r"const\s+CONFIG_INVITE_TEXT\s*=\s*'[^']*';",
                f"const CONFIG_INVITE_TEXT = '{new_text.replace(chr(39), chr(92) + chr(39))}';",
                content,
            )
            content = re.sub(
                r"const\s+CONFIG_TANGGAL_DATE\s*=\s*'[^']*';",
                f"const CONFIG_TANGGAL_DATE = '{new_tanggal_date}';",
                content,
            )
            # 3. Fallback direct string replace for legacy/test HTML
            content = content.replace("SABTU, 5 DESEMBER 2026", new_text)
            invite_file.write_text(content, encoding="utf-8")

        yes_file = workspace_path / "frontend" / "src" / "yes.html"
        if yes_file.exists():
            content = yes_file.read_text(encoding="utf-8")
            if new_target:
                content = re.sub(
                    r"const\s+TARGET\s*=\s*new\s+Date\('[^']*'\);",
                    f"const TARGET = new Date('{new_target}');",
                    content,
                )
                content = content.replace("new Date('2026-12-05T12:00:00Z')", f"new Date('{new_target}')")
            if new_text:
                content = re.sub(
                    r"const\s+CONFIG_INVITE_TEXT\s*=\s*'[^']*';",
                    f"const CONFIG_INVITE_TEXT = '{new_text.replace(chr(39), chr(92) + chr(39))}';",
                    content,
                )
            yes_file.write_text(content, encoding="utf-8")
