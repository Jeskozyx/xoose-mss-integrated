"""
Command-line interface for Xoose Builder Engine.
Communicates with Laravel via JSON stdout and structured exit codes.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Ensure Windows user environment variables are populated when invoked from web servers (Apache / PHP-FPM)
if sys.platform == "win32":
    if not os.environ.get("USERPROFILE"):
        username = os.environ.get("USERNAME") or "Jeskozyx"
        sys_drive = os.environ.get("SystemDrive", "C:")
        candidate = os.path.join(sys_drive, "Users", username)
        if not os.path.exists(candidate):
            candidate = r"C:\Users\Jeskozyx"
        os.environ["USERPROFILE"] = candidate
        os.environ["HOMEDRIVE"] = os.path.splitdrive(candidate)[0] or "C:"
        os.environ["HOMEPATH"] = os.path.splitdrive(candidate)[1] or f"\\Users\\{username}"

    up = os.environ["USERPROFILE"]
    if not os.environ.get("APPDATA"):
        os.environ["APPDATA"] = os.path.join(up, "AppData", "Roaming")
    if not os.environ.get("LOCALAPPDATA"):
        os.environ["LOCALAPPDATA"] = os.path.join(up, "AppData", "Local")

    sys_path = os.environ.get("PATH") or os.environ.get("Path", "")
    if not sys_path:
        sys_path = r"C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;C:\Users\Jeskozyx\AppData\Local\Programs\Python\Python314\Scripts;C:\Users\Jeskozyx\AppData\Local\Programs\Python\Python314"
    os.environ["PATH"] = sys_path
    os.environ["Path"] = sys_path

from xoose_builder.builder import BuildEngine
from xoose_builder.exceptions import BuilderError
from xoose_builder.manifest import Manifest
from xoose_builder.workspace import WorkspaceManager

# Setup stderr logger for diagnostics so stdout remains clean JSON
logger = logging.getLogger("xoose_builder")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def print_json_response(data: dict, exit_code: int = 0):
    """Outputs JSON response to stdout and exits."""
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def handle_validate(args):
    """Handles 'validate' subcommand."""
    manifest = Manifest.from_file(args.manifest)
    resp = {
        "success": True,
        "status": "valid",
        "project_slug": manifest.app_slug,
        "app_name": manifest.app_name,
        "app_version": manifest.app_version,
        "template_id": manifest.template_id,
        "template_source": str(manifest.template_source_path).replace("\\", "/"),
        "build_format": manifest.build_format,
        "entry_point": manifest.entry_point,
    }
    print_json_response(resp, 0)


def handle_workspace(args):
    """Handles 'workspace' subcommand."""
    manifest = Manifest.from_file(args.manifest)
    workspace_root = args.workspace_root or "D:/KULIAH/KODINGAN/xoose-loveyou/workspace"

    manager = WorkspaceManager(workspace_root)
    workspace_path = manager.create_workspace(manifest, force=args.force)

    resp = {
        "success": True,
        "status": "workspace_created",
        "project_slug": manifest.app_slug,
        "workspace_path": str(workspace_path).replace("\\", "/"),
    }
    print_json_response(resp, 0)


def handle_build(args):
    """Handles 'build' subcommand executing PyInstaller."""
    manifest = Manifest.from_file(args.manifest)
    workspace_root = args.workspace_root or "D:/KULIAH/KODINGAN/xoose-loveyou/workspace"
    output_dir = args.output_dir or "D:/KULIAH/KODINGAN/xoose-loveyou/builds"
    logs_dir = args.logs_dir or "D:/KULIAH/KODINGAN/xoose-loveyou/logs"

    manager = WorkspaceManager(workspace_root)
    workspace_path = manager.get_project_workspace_path(manifest.app_slug)

    if not workspace_path.exists() or args.force:
        workspace_path = manager.create_workspace(manifest, force=args.force)
    else:
        # Pastikan konfigurasi dan kustomisasi tanggal terbaru selalu diterapkan sebelum build
        manager._apply_configuration(workspace_path, manifest)

    engine = BuildEngine(
        workspace_path=workspace_path,
        output_dir=Path(output_dir),
        logs_dir=Path(logs_dir),
    )

    result = engine.build(
        manifest=manifest,
        build_id=args.build_id,
        format_override=args.format,
    )
    print_json_response(result, 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xoose-builder",
        description="Xoose Python Build Engine CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    validate_p = subparsers.add_parser("validate", help="Validate manifest schema and paths")
    validate_p.add_argument("--manifest", required=True, help="Path to manifest JSON file")
    validate_p.set_defaults(func=handle_validate)

    # workspace
    workspace_p = subparsers.add_parser("workspace", help="Create isolated workspace from template")
    workspace_p.add_argument("--manifest", required=True, help="Path to manifest JSON file")
    workspace_p.add_argument("--workspace-root", default=None, help="Root workspace directory")
    workspace_p.add_argument("--force", action="store_true", help="Overwrite existing workspace")
    workspace_p.set_defaults(func=handle_workspace)

    # build
    build_p = subparsers.add_parser("build", help="Run PyInstaller build")
    build_p.add_argument("--manifest", required=True, help="Path to manifest JSON file")
    build_p.add_argument("--workspace-root", default=None, help="Root workspace directory")
    build_p.add_argument("--output-dir", default=None, help="Target build output directory")
    build_p.add_argument("--logs-dir", default=None, help="Target logs directory")
    build_p.add_argument("--build-id", default=None, help="Unique build identifier")
    build_p.add_argument("--format", choices=["onedir", "onefile"], default=None, help="Build format override")
    build_p.add_argument("--force", action="store_true", help="Force rebuild/overwrite workspace")
    build_p.set_defaults(func=handle_build)

    return parser


def main():
    parser = build_parser()
    try:
        args = parser.parse_args()
        args.func(args)
    except BuilderError as e:
        logger.error("BuilderError: %s (%s)", e.message, e.code)
        print_json_response(e.to_dict(), exit_code=1)
    except Exception as e:
        logger.exception("Unexpected error: %s", str(e))
        err_dict = {
            "success": False,
            "error": str(e),
            "code": "UNEXPECTED_ERROR",
        }
        print_json_response(err_dict, exit_code=2)


if __name__ == "__main__":
    main()
