import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestCli(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root_p = Path(self.temp_dir)

        # Create mock template
        self.template_dir = self.root_p / "mock_template"
        self.template_dir.mkdir()
        (self.template_dir / "backend").mkdir()
        (self.template_dir / "backend" / "screenshot_service.py").write_text("# entry", encoding="utf-8")
        (self.template_dir / "backend" / "config.ini").write_text("[SUPABASE]\nurl = https://test.supabase.co\n", encoding="utf-8")

        self.workspace_root = self.root_p / "workspace"
        self.workspace_root.mkdir()

        # Create valid manifest file
        self.manifest_file = self.root_p / "manifest.json"
        manifest_data = {
            "template": {
                "id": "loveyou",
                "name": "LoveYou",
                "version": "1.0.0",
                "source_path": str(self.template_dir).replace("\\", "/"),
            },
            "application": {
                "name": "CLI Test App",
                "slug": "cli-test-app",
                "version": "1.0.0",
            },
            "build": {
                "platform": "windows",
                "format": "onedir",
                "entry_point": "backend/screenshot_service.py",
            },
            "features": {},
            "configuration": {},
        }
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_cli(self, args):
        cmd = [sys.executable, "-m", "xoose_builder.cli"] + args
        env = os.environ.copy()
        # Ensure builder/src is in PYTHONPATH
        src_path = str(Path(__file__).parent.parent / "src")
        env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return proc

    def test_cli_validate_success(self):
        proc = self.run_cli(["validate", "--manifest", str(self.manifest_file)])
        self.assertEqual(proc.returncode, 0, f"Stderr: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "valid")
        self.assertEqual(data.get("project_slug"), "cli-test-app")

    def test_cli_validate_nonexistent_manifest(self):
        proc = self.run_cli(["validate", "--manifest", "nonexistent.json"])
        self.assertNotEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("code"), "MANIFEST_NOT_FOUND")

    def test_cli_workspace_creation(self):
        proc = self.run_cli([
            "workspace",
            "--manifest", str(self.manifest_file),
            "--workspace-root", str(self.workspace_root),
        ])
        self.assertEqual(proc.returncode, 0, f"Stderr: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "workspace_created")

        ws_path = Path(data["workspace_path"])
        self.assertTrue(ws_path.exists())
        self.assertTrue((ws_path / "backend" / "screenshot_service.py").exists())


if __name__ == "__main__":
    unittest.main()
