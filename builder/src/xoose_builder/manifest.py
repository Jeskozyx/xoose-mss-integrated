"""
Manifest schema parser and validator for Xoose Builder.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from xoose_builder.exceptions import (
    InvalidSlugError,
    PathTraversalError,
    TemplateNotFoundError,
    ValidationError,
)

SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_slug(slug: str) -> str:
    """Validate slug for safe folder naming and routing."""
    if not isinstance(slug, str):
        raise InvalidSlugError("Slug must be a string")

    slug = slug.strip()
    if not slug:
        raise InvalidSlugError("Slug cannot be empty")

    if len(slug) < 3 or len(slug) > 64:
        raise InvalidSlugError("Slug length must be between 3 and 64 characters")

    if not SLUG_REGEX.match(slug):
        raise InvalidSlugError(
            f"Invalid slug '{slug}'. Must contain only lowercase alphanumeric characters and single hyphens."
        )

    return slug


def ensure_path_contained(base_path: Path, target_path: Path) -> Path:
    """
    Ensure target_path is strictly inside base_path (no path traversal).
    Returns resolved absolute target path.
    """
    resolved_base = base_path.resolve()
    resolved_target = target_path.resolve()

    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        raise PathTraversalError(
            f"Path '{resolved_target}' escapes allowed base directory '{resolved_base}'"
        )

    return resolved_target


class Manifest:
    """Represents a validated application build manifest."""

    def __init__(self, data: Dict[str, Any], manifest_file_path: Optional[str] = None):
        self.raw_data = data
        self.manifest_file_path = manifest_file_path
        self._validate()

    @classmethod
    def from_file(cls, path: str) -> "Manifest":
        if not os.path.exists(path):
            raise ValidationError(f"Manifest file not found: {path}", code="MANIFEST_NOT_FOUND")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in manifest file: {e}", code="INVALID_JSON")
        except Exception as e:
            raise ValidationError(f"Cannot read manifest file: {e}", code="FILE_READ_ERROR")

        return cls(data, manifest_file_path=path)

    @classmethod
    def from_json_string(cls, content: str) -> "Manifest":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}", code="INVALID_JSON")
        return cls(data)

    def _validate(self):
        if not isinstance(self.raw_data, dict):
            raise ValidationError("Manifest root must be a JSON object", code="INVALID_SCHEMA")

        # 1. Template validation
        template = self.raw_data.get("template")
        if not isinstance(template, dict):
            raise ValidationError("Missing 'template' section in manifest", code="MISSING_SECTION")

        self.template_id = str(template.get("id", "")).strip()
        self.template_name = str(template.get("name", "")).strip()
        self.template_version = str(template.get("version", "1.0.0")).strip()
        self.template_source = str(template.get("source_path", "")).strip()

        if not self.template_id:
            raise ValidationError("Template 'id' cannot be empty", code="INVALID_TEMPLATE")
        if not self.template_source:
            raise ValidationError("Template 'source_path' cannot be empty", code="INVALID_TEMPLATE")

        source_p = Path(self.template_source).resolve()
        if not source_p.exists() or not source_p.is_dir():
            raise TemplateNotFoundError(f"Template source directory not found: {self.template_source}")
        self.template_source_path = source_p

        # 2. Application validation
        application = self.raw_data.get("application")
        if not isinstance(application, dict):
            raise ValidationError("Missing 'application' section in manifest", code="MISSING_SECTION")

        self.app_name = str(application.get("name", "")).strip()
        if not self.app_name:
            raise ValidationError("Application 'name' cannot be empty", code="INVALID_APP_NAME")

        raw_slug = application.get("slug", "")
        self.app_slug = validate_slug(raw_slug)
        self.app_version = str(application.get("version", "1.0.0")).strip()

        # 3. Build settings validation
        build_conf = self.raw_data.get("build", {})
        if not isinstance(build_conf, dict):
            raise ValidationError("'build' section must be an object", code="INVALID_BUILD_CONFIG")

        self.build_platform = str(build_conf.get("platform", "windows")).lower()
        if self.build_platform != "windows":
            raise ValidationError("Currently only 'windows' platform is supported", code="UNSUPPORTED_PLATFORM")

        self.build_format = str(build_conf.get("format", "onedir")).lower()
        if self.build_format not in ["onedir", "onefile"]:
            raise ValidationError("Build format must be 'onedir' or 'onefile'", code="INVALID_BUILD_FORMAT")

        self.entry_point = str(build_conf.get("entry_point", "backend/screenshot_service.py")).strip().replace("\\", "/")
        if not self.entry_point:
            raise ValidationError("Entry point cannot be empty", code="INVALID_ENTRY_POINT")

        # Icon selection (defaults to heart.ico)
        self.icon_file = str(build_conf.get("icon", "heart.ico")).strip().replace("\\", "/")

        # Verify entry point inside template
        entry_abs = self.template_source_path / self.entry_point
        if not entry_abs.exists():
            raise TemplateNotFoundError(
                f"Entry point '{self.entry_point}' not found in template directory '{self.template_source_path}'"
            )

        # 4. Features & Configurations
        self.features: Dict[str, Any] = self.raw_data.get("features", {})
        if not isinstance(self.features, dict):
            raise ValidationError("'features' section must be an object", code="INVALID_FEATURES")

        self.configuration: Dict[str, Any] = self.raw_data.get("configuration", {})
        if not isinstance(self.configuration, dict):
            raise ValidationError("'configuration' section must be an object", code="INVALID_CONFIGURATION")

        # 5. Editable files allowlist
        editable = self.raw_data.get("editable_files", [])
        if not isinstance(editable, list):
            raise ValidationError("'editable_files' must be a list of file paths", code="INVALID_EDITABLE_FILES")

        self.editable_files: List[str] = []
        for f in editable:
            f_str = str(f).strip().replace("\\", "/")
            if not f_str or f_str.startswith("/") or ".." in f_str:
                raise PathTraversalError(f"Invalid editable file path: {f}")
            self.editable_files.append(f_str)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template": {
                "id": self.template_id,
                "name": self.template_name,
                "version": self.template_version,
                "source_path": str(self.template_source_path).replace("\\", "/"),
            },
            "application": {
                "name": self.app_name,
                "slug": self.app_slug,
                "version": self.app_version,
            },
            "build": {
                "platform": self.build_platform,
                "format": self.build_format,
                "entry_point": self.entry_point,
                "icon": self.icon_file,
            },
            "features": self.features,
            "configuration": self.configuration,
            "editable_files": self.editable_files,
        }
