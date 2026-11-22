"""
Cryptographic checksum (SHA-256) and HMAC-SHA256 release signing utilities for Xoose Builder.
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path


def compute_sha256(file_path: str | Path) -> str:
    """Compute lowercase hexadecimal SHA-256 checksum for a build artifact."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def sign_checksum_hmac(sha256_checksum: str, signing_key: str) -> str:
    """Create HMAC-SHA256 signature over a lowercase SHA-256 hex digest."""
    if not sha256_checksum or not signing_key:
        raise ValueError("Both sha256_checksum and signing_key must be non-empty.")
    return hmac.new(
        signing_key.encode("utf-8"),
        sha256_checksum.strip().lower().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().lower()


def verify_checksum_hmac(sha256_checksum: str, signature: str, signing_key: str) -> bool:
    """Verify HMAC-SHA256 signature in constant time."""
    if not sha256_checksum or not signature or not signing_key:
        return False
    expected = sign_checksum_hmac(sha256_checksum, signing_key)
    return hmac.compare_digest(expected, signature.strip().lower())
