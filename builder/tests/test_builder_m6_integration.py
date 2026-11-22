"""
Milestone 6 — Pengujian Integrasi Python Build Engine (xoose_builder):
- Isolasi penuh 2 aplikasi berbeda dari template LoveYou asli (tanpa mengubah template)
- Agent & 7 modular services terpasang utuh di tiap workspace build
- Injeksi [AGENT] per proyek tanpa shared credential / tanpa service_role key
- Guard keras penolakan secret (service_role, sb_secret_, device_token, xly_dev_)
- Sanitasi log build & integritas SHA-256 / HMAC signer
"""

from __future__ import annotations

import configparser
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from xoose_builder.builder import sanitize_log_line
from xoose_builder.exceptions import ValidationError
from xoose_builder.manifest import Manifest
from xoose_builder.signer import compute_sha256, sign_checksum_hmac, verify_checksum_hmac
from xoose_builder.workspace import WorkspaceManager

REAL_TEMPLATE_DIR = Path(r"D:\KULIAH\KODINGAN\screenshotusingpy")


def _make_manifest_dict(
    app_name: str,
    slug: str,
    version: str,
    icon: str,
    interval: int,
    invite_text: str,
    api_url: str,
    enrollment_code: str,
) -> dict:
    return {
        "template": {
            "id": "loveyou",
            "name": "LoveYou Modular Template",
            "version": "1.0.0",
            "source_path": str(REAL_TEMPLATE_DIR),
        },
        "application": {
            "name": app_name,
            "slug": slug,
            "version": version,
        },
        "build": {
            "platform": "windows",
            "format": "onefile",
            "entry_point": "backend/screenshot_service.py",
            "icon": icon,
        },
        "agent": {
            "enabled": True,
            "api_base_url": api_url,
            "project_slug": slug,
            "enrollment_code": enrollment_code,
            "heartbeat_interval_seconds": 25,
            "poll_interval_seconds": 8,
            "config_sync_interval_seconds": 45,
            "realtime_enabled": False,
            "app_version": version,
        },
        "features": {
            "auto_start": False,
            "keep_local_file": False,
            "emergency_uninstall_hotkey": True,
        },
        "configuration": {
            "supabase_url": "https://wqjfunxfngowxwdmyzyj.supabase.co",
            "supabase_key": "sb_publishable_u2lBe4CRF_2XEqbkniBjbw_p0gGEXgZ",
            "table_name": "hasil_ss",
            "bucket_name": "screenshots",
            "interval_seconds": interval,
            "image_format": "webp",
            "jpg_quality": 75,
            "date_invitation_text": invite_text,
            "date_countdown_target": "2026-12-05T12:00:00Z",
        },
        "editable_files": [
            "backend/config.ini",
            "frontend/src/invite.html",
            "frontend/src/yes.html",
        ],
    }


class TestBuilderMilestone6Integration(unittest.TestCase):
    def test_two_isolated_apps_include_agent_and_modular_services_without_leaking_secrets(self) -> None:
        if not REAL_TEMPLATE_DIR.exists():
            self.skipTest("Template LoveYou tidak ditemukan di path lokal.")

        original_template_ini = (REAL_TEMPLATE_DIR / "backend" / "config.ini").read_text(encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = WorkspaceManager(tmpdir)

            m_alpha = Manifest(
                _make_manifest_dict(
                    app_name="LoveYou Alpha",
                    slug="loveyou-alpha",
                    version="1.0.0",
                    icon="heart.ico",
                    interval=5,
                    invite_text="MINGGU, 27 DESEMBER 2026",
                    api_url="https://alpha.xoose.local",
                    enrollment_code="XLY-ALPH-0001-AAAA",
                )
            )
            m_beta = Manifest(
                _make_manifest_dict(
                    app_name="Chrome Beta",
                    slug="chrome-beta-game",
                    version="2.1.0",
                    icon="chrome.ico",
                    interval=15,
                    invite_text="JUMAT, 1 JANUARI 2027",
                    api_url="https://beta.xoose.local",
                    enrollment_code="XLY-BETA-0002-BBBB",
                )
            )

            ws_alpha = mgr.create_workspace(m_alpha, force=True)
            ws_beta = mgr.create_workspace(m_beta, force=True)

            self.assertNotEqual(ws_alpha, ws_beta)

            # Pastikan template asli tidak berubah sedikit pun
            self.assertEqual(
                (REAL_TEMPLATE_DIR / "backend" / "config.ini").read_text(encoding="utf-8"),
                original_template_ini,
            )

            # Verifikasi kedua workspace memiliki modul M1 (services + schemas) & M2 (agent), tanpa tests/ atau local credentials
            for ws, expected_slug, expected_url, expected_code, expected_ver, expected_interval, expected_icon in (
                (ws_alpha, "loveyou-alpha", "https://alpha.xoose.local", "XLY-ALPH-0001-AAAA", "1.0.0", 5, "heart.ico"),
                (ws_beta, "chrome-beta-game", "https://beta.xoose.local", "XLY-BETA-0002-BBBB", "2.1.0", 15, "chrome.ico"),
            ):
                self.assertTrue((ws / "backend" / "agent" / "runtime.py").exists())
                self.assertTrue((ws / "backend" / "agent" / "identity.py").exists())
                self.assertTrue((ws / "backend" / "services" / "manager.py").exists())
                self.assertTrue((ws / "backend" / "services" / "game.py").exists())
                self.assertTrue((ws / "backend" / "schemas" / "service_schemas.py").exists())

                # Jangan pernah menyalin tests/, .pytest_cache/, atau kredensial agent lokal ke workspace build
                self.assertFalse((ws / "tests").exists())
                self.assertFalse((ws / ".pytest_cache").exists())
                self.assertFalse((ws / "identity.json").exists())

                cfg_text = (ws / "backend" / "config.ini").read_text(encoding="utf-8")
                self.assertNotIn("service_role", cfg_text.lower())
                self.assertNotIn("sb_secret_", cfg_text.lower())
                self.assertNotIn("xly_dev_", cfg_text.lower())

                parser = configparser.ConfigParser()
                parser.read_string(cfg_text)
                self.assertEqual(parser["AGENT"]["enabled"], "true")
                self.assertEqual(parser["AGENT"]["api_base_url"], expected_url)
                self.assertEqual(parser["AGENT"]["project_slug"], expected_slug)
                self.assertEqual(parser["AGENT"]["enrollment_code"], expected_code)
                self.assertEqual(parser["AGENT"]["app_version"], expected_ver)
                self.assertEqual(parser["CAPTURE"].getint("interval_seconds"), expected_interval)
                self.assertEqual(parser["TRAY"]["icon"], expected_icon)
                self.assertEqual(parser["STARTUP"]["auto_start"], "false")

                # Verifikasi entry point di dalam workspace dapat memuat seluruh modul M1 & M2 secara mandiri
                proc = subprocess.run(
                    [sys.executable, str(ws / "backend" / "screenshot_service.py"), "--help"],
                    cwd=str(ws / "backend"),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(proc.returncode, 0, f"Workspace {expected_slug} gagal bootstrap: {proc.stderr}")
                self.assertIn("--no-agent", proc.stdout)

    def test_forbidden_secrets_are_blocked_from_manifests(self) -> None:
        if not REAL_TEMPLATE_DIR.exists():
            self.skipTest("Template LoveYou tidak ditemukan di path lokal.")

        # 1. Blokir key service_role
        bad1 = _make_manifest_dict("Bad1", "bad-app-1", "1.0.0", "heart.ico", 3, "SABTU, 5 DESEMBER 2026", "http://localhost:8000", "XLY-1111-2222-3333")
        bad1["configuration"]["supabase_service_role_key"] = "secret"
        with self.assertRaises(ValidationError) as ctx1:
            Manifest(bad1)
        self.assertEqual(ctx1.exception.code, "FORBIDDEN_SECRET_IN_BUILD")

        # 2. Blokir value sb_secret_...
        bad2 = _make_manifest_dict("Bad2", "bad-app-2", "1.0.0", "heart.ico", 3, "SABTU, 5 DESEMBER 2026", "http://localhost:8000", "XLY-1111-2222-3333")
        bad2["configuration"]["supabase_key"] = "sb_secret_LEAKED_KEY_12345"
        with self.assertRaises(ValidationError) as ctx2:
            Manifest(bad2)
        self.assertEqual(ctx2.exception.code, "FORBIDDEN_SECRET_IN_BUILD")

        # 3. Blokir shared device_token (xly_dev_...)
        bad3 = _make_manifest_dict("Bad3", "bad-app-3", "1.0.0", "heart.ico", 3, "SABTU, 5 DESEMBER 2026", "http://localhost:8000", "xly_dev_sharedtoken99999")
        with self.assertRaises(ValidationError) as ctx3:
            Manifest(bad3)
        self.assertEqual(ctx3.exception.code, "FORBIDDEN_SECRET_IN_BUILD")

    def test_log_sanitization_and_signer_integrity(self) -> None:
        raw_log = "Using key sb_secret_ABC123 token xly_dev_deadbeef code XLY-AB12-CD34-EF56"
        cleaned = sanitize_log_line(raw_log)
        self.assertNotIn("sb_secret_", cleaned)
        self.assertNotIn("xly_dev_", cleaned)
        self.assertNotIn("XLY-AB12-CD34-EF56", cleaned)
        self.assertIn("[REDACTED_SECRET]", cleaned)

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "app.exe"
            artifact.write_bytes(b"MOCK_EXE_BINARY_CONTENT")
            digest = compute_sha256(artifact)
            self.assertEqual(len(digest), 64)
            sig = sign_checksum_hmac(digest, "server-signing-key")
            self.assertTrue(verify_checksum_hmac(digest, sig, "server-signing-key"))
            self.assertFalse(verify_checksum_hmac(digest, sig, "wrong-key"))


if __name__ == "__main__":
    unittest.main()
