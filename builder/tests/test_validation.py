import unittest
from pathlib import Path

from xoose_builder.exceptions import (
    InvalidSlugError,
    PathTraversalError,
    TemplateNotFoundError,
    ValidationError,
)
from xoose_builder.manifest import Manifest, ensure_path_contained, validate_slug


class TestSlugValidation(unittest.TestCase):
    def test_valid_slugs(self):
        valid = ["contoh-app", "loveyou-app", "my-project-123", "abc", "a-b-c"]
        for s in valid:
            self.assertEqual(validate_slug(s), s)

    def test_invalid_slugs(self):
        invalid = [
            "",
            "ab",  # too short (< 3)
            "a" * 65,  # too long (> 64)
            "Contoh-App",  # uppercase
            "contoh app",  # space
            "contoh_app",  # underscore
            "contoh..app",  # double dot
            "../bad-slug",  # path traversal
            "bad/slug",
            "-leading-hyphen",
            "trailing-hyphen-",
            "double--hyphen",
        ]
        for s in invalid:
            with self.subTest(slug=s):
                with self.assertRaises(InvalidSlugError):
                    validate_slug(s)


class TestPathTraversal(unittest.TestCase):
    def test_contained_path(self):
        base = Path("C:/project/root")
        target = Path("C:/project/root/subdir/file.txt")
        # In a mock or non-resolving test, check relative containment
        try:
            resolved_base = Path(".").resolve()
            resolved_target = (resolved_base / "subdir").resolve()
            result = ensure_path_contained(resolved_base, resolved_target)
            self.assertEqual(result, resolved_target)
        except Exception as e:
            self.fail(f"Contained path raised error: {e}")

    def test_escaping_path(self):
        base = Path(".").resolve()
        target = (base / ".." / "escaped").resolve()
        with self.assertRaises(PathTraversalError):
            ensure_path_contained(base, target)


class TestManifestValidation(unittest.TestCase):
    def test_manifest_missing_sections(self):
        with self.assertRaises(ValidationError):
            Manifest.from_json_string("{}")

    def test_manifest_missing_application(self):
        with self.assertRaises(ValidationError):
            Manifest.from_json_string('{"template": {"id": "test", "name": "Test", "source_path": "."}}')


if __name__ == "__main__":
    unittest.main()
