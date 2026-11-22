import json
import shutil
import tempfile
import unittest
from pathlib import Path

from xoose_builder.exceptions import WorkspaceCollisionError
from xoose_builder.manifest import Manifest
from xoose_builder.workspace import WorkspaceManager


class TestWorkspaceManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root_p = Path(self.temp_dir)

        # Create mock template
        self.template_dir = self.root_p / "mock_template"
        self.template_dir.mkdir()
        (self.template_dir / "backend").mkdir()
        (self.template_dir / "backend" / "screenshot_service.py").write_text("# entry", encoding="utf-8")
        (self.template_dir / "backend" / "config.ini").write_text("[SUPABASE]\nurl = https://old.supabase.co\n", encoding="utf-8")

        # Create ignored items in template
        (self.template_dir / ".git").mkdir()
        (self.template_dir / ".git" / "config").write_text("git config", encoding="utf-8")
        (self.template_dir / ".venv").mkdir()
        (self.template_dir / "test.pyc").write_text("pyc", encoding="utf-8")
        (self.template_dir / "loveyou.exe").write_text("exe", encoding="utf-8")
        (self.template_dir / "screenshots").mkdir()
        (self.template_dir / "screenshots" / "dummy.jpg").write_text("jpg", encoding="utf-8")

        # Workspace destination root
        self.workspace_root = self.root_p / "workspace"
        self.workspace_root.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_workspace_clean_copy(self):
        manifest_data = {
            "template": {
                "id": "loveyou",
                "name": "LoveYou",
                "version": "1.0.0",
                "source_path": str(self.template_dir),
            },
            "application": {
                "name": "Aplikasi Uji",
                "slug": "aplikasi-uji",
                "version": "1.0.0",
            },
            "build": {
                "platform": "windows",
                "format": "onedir",
                "entry_point": "backend/screenshot_service.py",
            },
            "features": {
                "auto_start": True,
            },
            "configuration": {
                "supabase_url": "https://new.supabase.co",
            },
        }

        manifest = Manifest(manifest_data)
        manager = WorkspaceManager(str(self.workspace_root))
        ws_path = manager.create_workspace(manifest)

        # Assert destination created
        self.assertTrue(ws_path.exists())
        self.assertTrue((ws_path / "backend" / "screenshot_service.py").exists())

        # Assert ignored files are NOT copied
        self.assertFalse((ws_path / ".git").exists())
        self.assertFalse((ws_path / ".venv").exists())
        self.assertFalse((ws_path / "test.pyc").exists())
        self.assertFalse((ws_path / "loveyou.exe").exists())
        self.assertFalse((ws_path / "screenshots").exists())

        # Assert configuration was injected
        config_text = (ws_path / "backend" / "config.ini").read_text(encoding="utf-8")
        self.assertIn("https://new.supabase.co", config_text)

        # Assert collision error when creating again without force
        with self.assertRaises(WorkspaceCollisionError):
            manager.create_workspace(manifest, force=False)

        # Assert overwrite succeeds when force=True
        ws_recreated = manager.create_workspace(manifest, force=True)
        self.assertTrue(ws_recreated.exists())


if __name__ == "__main__":
    unittest.main()
