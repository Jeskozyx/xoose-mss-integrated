"""
ImageAssembler: Penyusun chunk gambar Base64 dari Native Messaging Extension
dengan verifikasi keamanan lengkap dan penulisan atomik ke folder spool LoveYou.

Fitur Keamanan & Integritas:
- Validasi UUID ketat pada capture_id (mencegah path traversal)
- Guard jumlah chunk (<= 64), urutan, duplikasi chunk, batas payload (<= 10 MB)
- Pembersihan otomatis buffer kedaluwarsa (timeout 30 detik)
- Verifikasi SHA-256 byte gambar utuh sebelum decode Pillow
- Konversi deterministik ke WEBP (kualitas optimal) dengan fallback otomatis ke PNG
- Atomic rename (.tmp -> spool/incoming/<capture_id>.<ext> + .meta.json)
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from PIL import Image

MAX_CHUNKS = 64
MAX_CHUNK_BASE64_CHARS = 350 * 1024
MAX_TOTAL_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_ASSEMBLY_TIMEOUT_SECONDS = 30.0

ALLOWED_INPUT_MIMES = frozenset({"image/png", "image/jpeg", "image/webp"})
ALLOWED_TARGET_FORMATS = frozenset({"webp", "png", "jpeg"})
ALLOWED_BROWSERS = frozenset({"chrome", "edge", "firefox"})
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{1,80}$")


class AssemblyError(Exception):
    """Error validasi atau assembly chunk gambar."""

    def __init__(self, message: str, code: str = "ASSEMBLY_ERROR", capture_id: str = ""):
        super().__init__(message)
        self.code = code
        self.capture_id = capture_id


@dataclass
class _PendingCapture:
    capture_id: str
    chunk_count: int
    mime_type: str
    target_format: str
    checksum: str
    created_at: float
    meta: dict[str, Any] = field(default_factory=dict)
    chunks: dict[int, str] = field(default_factory=dict)
    total_b64_chars: int = 0


def _validate_uuid(raw_id: Any) -> str:
    if not isinstance(raw_id, str):
        raise AssemblyError("capture_id wajib berupa UUID string valid.", code="INVALID_CAPTURE_ID")
    cleaned = raw_id.strip()
    try:
        parsed = uuid.UUID(cleaned)
    except ValueError as exc:
        raise AssemblyError(f"capture_id bukan UUID valid: '{cleaned}'.", code="INVALID_CAPTURE_ID") from exc
    return str(parsed)


def _sanitize_meta(raw_meta: Any) -> dict[str, Any]:
    if not isinstance(raw_meta, dict):
        return {}
    browser = str(raw_meta.get("browser", "chrome")).strip().lower()
    if browser not in ALLOWED_BROWSERS:
        browser = "chrome"

    rule_id = str(raw_meta.get("rule_id", "")).strip()
    if rule_id and not SAFE_ID_RE.match(rule_id):
        rule_id = re.sub(r"[^a-zA-Z0-9._-]", "_", rule_id)[:64]

    origin_domain = str(raw_meta.get("origin_domain", "")).strip().lower()
    # Pastikan tidak pernah menyimpan query string, fragment, atau path
    origin_domain = origin_domain.split("/")[0].split("?")[0].split("#")[0][:253]

    captured_at = str(raw_meta.get("captured_at", "")).strip()
    if not captured_at:
        captured_at = datetime.now(timezone.utc).isoformat()

    return {
        "source": "browser_tab",
        "browser": browser,
        "rule_id": rule_id,
        "origin_domain": origin_domain,
        "captured_at": captured_at,
    }


class ImageAssembler:
    """Menyusun chunk gambar secara aman dan menulis hasil final ke spool/incoming secara atomik."""

    def __init__(
        self,
        spool_root: str | Path,
        max_image_bytes: int = MAX_TOTAL_IMAGE_BYTES,
        max_chunks: int = MAX_CHUNKS,
        timeout_seconds: float = DEFAULT_ASSEMBLY_TIMEOUT_SECONDS,
        now_fn: Callable[[], float] | None = None,
        device_id_fn: Callable[[], str] | None = None,
    ):
        self.spool_root = Path(spool_root).resolve()
        self.incoming_dir = self.spool_root / "incoming"
        self.tmp_dir = self.spool_root / "tmp"
        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        self.max_image_bytes = int(max_image_bytes)
        self.max_chunks = int(max_chunks)
        self.timeout_seconds = float(timeout_seconds)
        self._now = now_fn or time.monotonic
        self._device_id_fn = device_id_fn or (lambda: "")

        self._lock = threading.RLock()
        self._pending: dict[str, _PendingCapture] = {}

    def cleanup_expired(self) -> list[str]:
        """Membersihkan sesi assembly yang melebihi batas waktu timeout."""
        now = self._now()
        expired_ids: list[str] = []
        with self._lock:
            for cid, entry in list(self._pending.items()):
                if now - entry.created_at > self.timeout_seconds:
                    expired_ids.append(cid)
                    del self._pending[cid]
        return expired_ids

    def abort(self, capture_id: str) -> bool:
        """Membatalkan assembly yang sedang berlangsung."""
        try:
            cid = _validate_uuid(capture_id)
        except AssemblyError:
            return False
        with self._lock:
            return self._pending.pop(cid, None) is not None

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def add_chunk(self, msg: dict[str, Any]) -> dict[str, Any]:
        """
        Memproses satu pesan `capture_chunk`.
        Jika belum lengkap, mengembalikan `{"completed": False, ...}`.
        Jika lengkap dan lulus verifikasi SHA-256 + Pillow, menulis file atomik dan mengembalikan hasil spool.
        """
        self.cleanup_expired()

        capture_id = _validate_uuid(msg.get("capture_id"))
        chunk_index = msg.get("chunk_index")
        chunk_count = msg.get("chunk_count")
        mime_type = str(msg.get("mime_type", "image/png")).strip().lower()
        target_format = str(msg.get("target_format", "webp")).strip().lower()
        payload = msg.get("payload")
        checksum = str(msg.get("checksum", "")).strip().lower()

        if not isinstance(chunk_count, int) or isinstance(chunk_count, bool) or chunk_count < 1 or chunk_count > self.max_chunks:
            raise AssemblyError(
                f"chunk_count ({chunk_count}) di luar batas 1..{self.max_chunks}.",
                code="INVALID_CHUNK_COUNT",
                capture_id=capture_id,
            )

        if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index < 0 or chunk_index >= chunk_count:
            raise AssemblyError(
                f"chunk_index ({chunk_index}) tidak valid untuk chunk_count={chunk_count}.",
                code="INVALID_CHUNK_INDEX",
                capture_id=capture_id,
            )

        if mime_type not in ALLOWED_INPUT_MIMES:
            raise AssemblyError(f"mime_type '{mime_type}' tidak diizinkan.", code="INVALID_MIME", capture_id=capture_id)

        if target_format not in ALLOWED_TARGET_FORMATS:
            target_format = "webp"

        if not isinstance(payload, str) or not payload:
            raise AssemblyError("payload chunk kosong atau bukan string base64.", code="INVALID_PAYLOAD", capture_id=capture_id)

        if len(payload) > MAX_CHUNK_BASE64_CHARS:
            raise AssemblyError(
                f"Ukuran chunk ({len(payload)} char) melebihi batas {MAX_CHUNK_BASE64_CHARS}.",
                code="CHUNK_TOO_LARGE",
                capture_id=capture_id,
            )

        if not SHA256_HEX_RE.match(checksum):
            raise AssemblyError("Format checksum SHA-256 tidak valid (wajib 64 hex).", code="INVALID_CHECKSUM", capture_id=capture_id)

        with self._lock:
            entry = self._pending.get(capture_id)
            if entry is None:
                entry = _PendingCapture(
                    capture_id=capture_id,
                    chunk_count=chunk_count,
                    mime_type=mime_type,
                    target_format=target_format,
                    checksum=checksum,
                    created_at=self._now(),
                    meta=_sanitize_meta(msg.get("meta")),
                )
                self._pending[capture_id] = entry
            else:
                if entry.chunk_count != chunk_count or entry.checksum != checksum:
                    del self._pending[capture_id]
                    raise AssemblyError(
                        "Inkonsistensi chunk_count atau checksum antar chunk.",
                        code="CHUNK_MISMATCH",
                        capture_id=capture_id,
                    )
                if chunk_index in entry.chunks:
                    raise AssemblyError(
                        f"Chunk duplikat terdeteksi pada indeks {chunk_index}.",
                        code="DUPLICATE_CHUNK",
                        capture_id=capture_id,
                    )
                if not entry.meta and msg.get("meta"):
                    entry.meta = _sanitize_meta(msg.get("meta"))

            # Estimasi kasar ukuran byte (3/4 dari base64) sebelum penuh
            projected_bytes = ((entry.total_b64_chars + len(payload)) * 3) // 4
            if projected_bytes > self.max_image_bytes:
                del self._pending[capture_id]
                raise AssemblyError(
                    f"Total payload melebihi batas maksimum {self.max_image_bytes} byte.",
                    code="PAYLOAD_TOO_LARGE",
                    capture_id=capture_id,
                )

            entry.chunks[chunk_index] = payload
            entry.total_b64_chars += len(payload)

            if len(entry.chunks) < entry.chunk_count:
                return {
                    "completed": False,
                    "capture_id": capture_id,
                    "received_chunks": len(entry.chunks),
                    "chunk_count": entry.chunk_count,
                }

            # Lengkap — keluarkan dari pending dan rakit berdasarkan urutan indeks 0..chunk_count-1
            del self._pending[capture_id]

        return self._finalize_capture(entry)

    def _finalize_capture(self, entry: _PendingCapture) -> dict[str, Any]:
        # Rakit sesuai urutan indeks 0..chunk_count-1 (tahan terhadap urutan kedatangan acak)
        ordered_b64 = "".join(entry.chunks[i] for i in range(entry.chunk_count))
        try:
            raw_bytes = base64.b64decode(ordered_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise AssemblyError(f"Payload base64 korup: {exc}", code="INVALID_BASE64", capture_id=entry.capture_id) from exc

        if len(raw_bytes) > self.max_image_bytes:
            raise AssemblyError("Ukuran gambar terdekode melebihi batas maksimum.", code="PAYLOAD_TOO_LARGE", capture_id=entry.capture_id)

        actual_raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        if actual_raw_sha != entry.checksum:
            raise AssemblyError(
                f"SHA-256 tidak cocok (diharapkan {entry.checksum[:12]}..., aktual {actual_raw_sha[:12]}...).",
                code="CHECKSUM_MISMATCH",
                capture_id=entry.capture_id,
            )

        # Validasi gambar & konversi ke WEBP (fallback ke PNG bila gagal)
        final_bytes, final_ext, final_mime, resolution = self._convert_and_validate_image(
            raw_bytes=raw_bytes,
            target_format=entry.target_format,
            capture_id=entry.capture_id,
        )
        final_sha = hashlib.sha256(final_bytes).hexdigest()

        # Penulisan atomik ke tmp -> os.replace ke incoming/
        image_filename = f"{entry.capture_id}.{final_ext}"
        meta_filename = f"{entry.capture_id}.meta.json"

        tmp_img_path = self.tmp_dir / f"{image_filename}.tmp"
        final_img_path = self.incoming_dir / image_filename

        tmp_meta_path = self.tmp_dir / f"{meta_filename}.tmp"
        final_meta_path = self.incoming_dir / meta_filename

        tmp_img_path.write_bytes(final_bytes)
        os.replace(tmp_img_path, final_img_path)

        metadata = {
            "capture_id": entry.capture_id,
            "source": "browser_tab",
            "browser": entry.meta.get("browser", "chrome"),
            "rule_id": entry.meta.get("rule_id", ""),
            "device_id": self._device_id_fn() or "",
            "origin_domain": entry.meta.get("origin_domain", ""),
            "captured_at": entry.meta.get("captured_at") or datetime.now(timezone.utc).isoformat(),
            "mime_type": final_mime,
            "image_checksum": final_sha,
            "raw_checksum": actual_raw_sha,
            "resolution": resolution,
            "file_size_bytes": len(final_bytes),
            "image_filename": image_filename,
        }

        tmp_meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_meta_path, final_meta_path)

        return {
            "completed": True,
            "capture_id": entry.capture_id,
            "image_path": str(final_img_path),
            "meta_path": str(final_meta_path),
            "mime_type": final_mime,
            "image_checksum": final_sha,
            "resolution": resolution,
            "file_size_bytes": len(final_bytes),
            "metadata": metadata,
        }

    def _convert_and_validate_image(
        self,
        raw_bytes: bytes,
        target_format: str,
        capture_id: str,
    ) -> tuple[bytes, str, str, str]:
        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img.load()
                width, height = img.size
                resolution = f"{width}x{height}"
                rgb_img = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img.copy()
        except Exception as exc:
            raise AssemblyError(f"Data gambar tidak valid: {exc}", code="INVALID_IMAGE", capture_id=capture_id) from exc

        out_buf = io.BytesIO()
        if target_format == "webp":
            try:
                rgb_img.save(out_buf, format="WEBP", quality=75, method=4)
                return out_buf.getvalue(), "webp", "image/webp", resolution
            except Exception:
                # Fallback deterministik ke PNG bila encoder WEBP tidak tersedia
                out_buf = io.BytesIO()
                rgb_img.save(out_buf, format="PNG", optimize=True)
                return out_buf.getvalue(), "png", "image/png", resolution

        if target_format == "jpeg":
            rgb_img.convert("RGB").save(out_buf, format="JPEG", quality=75, optimize=True)
            return out_buf.getvalue(), "jpg", "image/jpeg", resolution

        rgb_img.save(out_buf, format="PNG", optimize=True)
        return out_buf.getvalue(), "png", "image/png", resolution
