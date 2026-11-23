"""
Tests Milestone BC-6: Perluasan xoose_builder untuk bundling Extension Chromium/Firefox
+ Native Messaging Host + template manifest + installer/uninstaller Windows.
"""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from xoose_builder.browser_bundle import BrowserCaptureBundler
from xoose_builder.builder import BuildEngine

INTEGRATION_ROOT = Path(__file__).resolve().parent.parent.parent


def test_build_engine_hidden_imports_include_browser_capture_and_native_bridge():
    src = (INTEGRATION_ROOT / "builder" / "src" / "xoose_builder" / "builder.py").read_text(encoding="utf-8")
    assert '"services.browser_capture"' in src
    assert '"agent.native_bridge"' in src
    assert isinstance(BuildEngine, type)


def test_browser_capture_bundler_packages_extensions_manifests_and_installers(tmp_path: Path):
    bundler = BrowserCaptureBundler(
        integration_root=INTEGRATION_ROOT,
        output_dir=tmp_path / "builds",
        logs_dir=tmp_path / "logs",
    )

    result = bundler.bundle(bundle_id="test_bc6", skip_pyinstaller=True)
    assert result["success"] is True
    assert result["bundle_id"] == "test_bc6"

    bundle_dir = Path(result["bundle_dir"])
    assert (bundle_dir / "bundle-manifest.json").exists()
    assert Path(result["install_script"]).exists()
    assert Path(result["uninstall_script"]).exists()

    # Verifikasi paket Chromium & Firefox
    for variant in ("chromium", "firefox"):
        ext_info = result["extensions"][variant]
        ext_dir = Path(ext_info["dir"])
        ext_zip = Path(ext_info["zip"])
        assert (ext_dir / "manifest.json").exists()
        assert (ext_dir / "shared" / "domain-matcher.js").exists()
        assert (ext_dir / "shared" / "capture-controller.js").exists()
        assert ext_zip.exists()
        assert len(ext_info["zip_sha256"]) == 64

        with zipfile.ZipFile(ext_zip, "r") as zf:
            names = set(zf.namelist())
            assert "manifest.json" in names
            assert "shared/domain-matcher.js" in names
            assert "popup.html" in names

    # Verifikasi template manifest 3 browser ikut terpaket & tidak ada token rahasia
    for tpl in ("chrome.template.json", "edge.template.json", "firefox.template.json"):
        tpl_path = bundle_dir / "native-host" / "host_manifest" / tpl
        assert tpl_path.exists()
        raw = tpl_path.read_text(encoding="utf-8")
        assert "sb_secret_" not in raw and "xly_dev_" not in raw


def test_cli_bundle_browser_capture_subcommand_outputs_clean_json(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "xoose_builder.cli",
            "bundle-browser-capture",
            "--integration-root",
            str(INTEGRATION_ROOT),
            "--output-dir",
            str(tmp_path / "out"),
            "--logs-dir",
            str(tmp_path / "logs"),
            "--bundle-id",
            "cli_check",
            "--skip-pyinstaller",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    data = json.loads(proc.stdout)
    assert data["success"] is True
    assert data["bundle_id"] == "cli_check"
    assert data["native_host"]["mode"] == "python_script"
