import configparser
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from xoose_builder.manifest import Manifest
from xoose_builder.workspace import WorkspaceManager


class TestMultiProjectConfiguration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root_p = Path(self.temp_dir)

        # Create mock source template
        self.template_dir = self.root_p / "template_src"
        self.template_dir.mkdir()
        (self.template_dir / "backend").mkdir()
        (self.template_dir / "backend" / "screenshot_service.py").write_text("# entry", encoding="utf-8")
        (self.template_dir / "backend" / "config.ini").write_text(
            "[SUPABASE]\nurl = https://default.supabase.co\n"
            "[CAPTURE]\ninterval_seconds = 3\nimage_format = jpg\n"
            "[STARTUP]\nauto_start = false\napp_name = Default\n",
            encoding="utf-8"
        )
        (self.template_dir / "frontend").mkdir()
        (self.template_dir / "frontend" / "src").mkdir()
        (self.template_dir / "frontend" / "src" / "invite.html").write_text(
            "<div>SABTU, 5 DESEMBER 2026</div>", encoding="utf-8"
        )
        (self.template_dir / "frontend" / "src" / "yes.html").write_text(
            "const TARGET = new Date('2026-12-05T12:00:00Z');", encoding="utf-8"
        )

        self.workspace_root = self.root_p / "workspace"
        self.workspace_root.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_two_distinct_projects_isolation(self):
        manager = WorkspaceManager(str(self.workspace_root))

        # Project 1: Alpha
        manifest_alpha = Manifest({
            "template": {"id": "loveyou", "name": "LoveYou", "source_path": str(self.template_dir)},
            "application": {"name": "Project Alpha", "slug": "project-alpha"},
            "build": {"platform": "windows", "entry_point": "backend/screenshot_service.py"},
            "features": {"auto_start": True},
            "configuration": {
                "interval_seconds": 2,
                "image_format": "jpg",
                "date_invitation_text": "MINGGU, 10 JANUARI 2027",
            },
        })

        # Project 2: Beta
        manifest_beta = Manifest({
            "template": {"id": "loveyou", "name": "LoveYou", "source_path": str(self.template_dir)},
            "application": {"name": "Project Beta", "slug": "project-beta"},
            "build": {"platform": "windows", "entry_point": "backend/screenshot_service.py"},
            "features": {"auto_start": False},
            "configuration": {
                "interval_seconds": 15,
                "image_format": "png",
                "date_invitation_text": "SABTU, 14 FEBRUARI 2027",
            },
        })

        ws_alpha = manager.create_workspace(manifest_alpha)
        ws_beta = manager.create_workspace(manifest_beta)

        # 1. Verify Project Alpha workspace
        config_alpha = configparser.ConfigParser()
        config_alpha.read(ws_alpha / "backend" / "config.ini")
        self.assertEqual(config_alpha.getint("CAPTURE", "interval_seconds"), 2)
        self.assertEqual(config_alpha.get("CAPTURE", "image_format"), "jpg")
        self.assertEqual(config_alpha.getboolean("STARTUP", "auto_start"), True)
        self.assertEqual(config_alpha.get("STARTUP", "app_name"), "Project Alpha")
        invite_alpha = (ws_alpha / "frontend" / "src" / "invite.html").read_text(encoding="utf-8")
        self.assertIn("MINGGU, 10 JANUARI 2027", invite_alpha)
        yes_alpha = (ws_alpha / "frontend" / "src" / "yes.html").read_text(encoding="utf-8")
        self.assertIn("2027-01-10", yes_alpha)
        self.assertEqual(config_alpha.get("CONTENT", "date_invitation_text"), "MINGGU, 10 JANUARI 2027")
        self.assertEqual(config_alpha.get("CONTENT", "tanggal_date"), "2027-01-10")

        # 2. Verify Project Beta workspace
        config_beta = configparser.ConfigParser()
        config_beta.read(ws_beta / "backend" / "config.ini")
        self.assertEqual(config_beta.getint("CAPTURE", "interval_seconds"), 15)
        self.assertEqual(config_beta.get("CAPTURE", "image_format"), "png")
        self.assertEqual(config_beta.getboolean("STARTUP", "auto_start"), False)
        self.assertEqual(config_beta.get("STARTUP", "app_name"), "Project Beta")
        invite_beta = (ws_beta / "frontend" / "src" / "invite.html").read_text(encoding="utf-8")
        self.assertIn("SABTU, 14 FEBRUARI 2027", invite_beta)
        yes_beta = (ws_beta / "frontend" / "src" / "yes.html").read_text(encoding="utf-8")
        self.assertIn("2027-02-14", yes_beta)
        self.assertEqual(config_beta.get("CONTENT", "date_invitation_text"), "SABTU, 14 FEBRUARI 2027")
        self.assertEqual(config_beta.get("CONTENT", "tanggal_date"), "2027-02-14")

        # 3. Verify Source Template remains unchanged
        config_src = configparser.ConfigParser()
        config_src.read(self.template_dir / "backend" / "config.ini")
        self.assertEqual(config_src.getint("CAPTURE", "interval_seconds"), 3)
        self.assertEqual(config_src.get("STARTUP", "app_name"), "Default")


if __name__ == "__main__":
    unittest.main()
