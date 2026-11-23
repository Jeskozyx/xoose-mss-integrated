"""
Protokol Native Messaging (32-bit unsigned little-endian length-prefixed JSON)
untuk komunikasi stdin/stdout antara Browser Extension (Chrome/Edge/Firefox)
dan Native Host Python.

ATURAN KERAS:
- stdout EKSKLUSIF untuk frame biner protokol Native Messaging.
- Dilarang mencetak log apa pun ke stdout.
- Pada Windows, stdin/stdout wajib diset ke mode binary (O_BINARY) agar header panjang tidak rusak.
"""

from __future__ import annotations

import json
import os
import struct
import sys
import threading
from typing import Any, BinaryIO

MAX_INCOMING_MESSAGE_BYTES = 1 * 1024 * 1024  # 1 MB per frame chunk masuk
MAX_OUTGOING_MESSAGE_BYTES = 512 * 1024       # 512 KB (margin aman di bawah batas 1 MB browser)

ALLOWED_INCOMING_TYPES = frozenset({
    "hello",
    "ping",
    "get_config",
    "status_report",
    "capture_chunk",
    "capture_abort",
})

FORBIDDEN_INCOMING_KEYS = frozenset({
    "command",
    "shell",
    "exec",
    "cmd",
    "output_path",
    "file_path",
    "dest_path",
    "target_path",
})


class ProtocolError(Exception):
    """Error framing atau validasi protokol Native Messaging."""

    def __init__(self, message: str, code: str = "PROTOCOL_ERROR"):
        super().__init__(message)
        self.code = code


def configure_binary_stdio() -> None:
    """Memastikan stdin & stdout dalam mode binary pada Windows agar byte \\n tidak diubah ke \\r\\n."""
    if os.name == "nt":
        try:
            import msvcrt

            for stream in (sys.stdin, sys.stdout):
                if stream is not None and hasattr(stream, "fileno"):
                    msvcrt.setmode(stream.fileno(), os.O_BINARY)
        except Exception:
            pass


def encode_message(payload: dict[str, Any]) -> bytes:
    """Mengenkode dict JSON menjadi frame Native Messaging 32-bit length-prefixed."""
    if not isinstance(payload, dict):
        raise ProtocolError("Payload pesan keluar harus berupa dict JSON.", code="INVALID_OUTGOING_PAYLOAD")
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_OUTGOING_MESSAGE_BYTES:
        raise ProtocolError(
            f"Ukuran pesan keluar ({len(encoded)} byte) melebihi batas {MAX_OUTGOING_MESSAGE_BYTES} byte.",
            code="OUTGOING_TOO_LARGE",
        )
    return struct.pack("<I", len(encoded)) + encoded


def validate_incoming_message(msg: Any) -> dict[str, Any]:
    """Memvalidasi allowlist tipe pesan & menolak field berbahaya (shell/output path arbitrer)."""
    if not isinstance(msg, dict):
        raise ProtocolError("Pesan masuk wajib berupa objek JSON.", code="INVALID_MESSAGE")

    for bad_key in FORBIDDEN_INCOMING_KEYS:
        if bad_key in msg:
            raise ProtocolError(
                f"Field terlarang '{bad_key}' ditolak oleh kebijakan keamanan Native Host.",
                code="FORBIDDEN_FIELD",
            )

    msg_type = msg.get("type")
    if not isinstance(msg_type, str) or msg_type not in ALLOWED_INCOMING_TYPES:
        raise ProtocolError(
            f"Tipe pesan '{msg_type}' tidak termasuk allowlist Native Host.",
            code="DISALLOWED_MESSAGE_TYPE",
        )

    return msg


def read_message(stream: BinaryIO, max_bytes: int = MAX_INCOMING_MESSAGE_BYTES) -> dict[str, Any] | None:
    """
    Membaca satu frame 32-bit length-prefixed JSON dari stream biner.
    Mengembalikan None jika EOF bersih (browser menutup pipe).
    """
    header = stream.read(4)
    if not header:
        return None
    if len(header) < 4:
        raise ProtocolError("Header panjang 32-bit terpotong (truncated).", code="TRUNCATED_HEADER")

    (length,) = struct.unpack("<I", header)
    if length == 0:
        raise ProtocolError("Panjang pesan 0 tidak valid.", code="EMPTY_MESSAGE")
    if length > max_bytes:
        raise ProtocolError(
            f"Ukuran pesan masuk ({length} byte) melebihi batas maksimum ({max_bytes} byte).",
            code="MESSAGE_TOO_LARGE",
        )

    body = stream.read(length)
    if len(body) < length:
        raise ProtocolError("Payload pesan masuk terpotong sebelum selesai dibaca.", code="TRUNCATED_BODY")

    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"JSON pesan masuk tidak valid: {exc}", code="INVALID_JSON") from exc

    return validate_incoming_message(parsed)


class NativeStreamWriter:
    """Thread-safe writer yang menjamin seluruh tulis ke stdout hanya berupa frame protokol valid."""

    def __init__(self, stream: BinaryIO):
        self._stream = stream
        self._lock = threading.Lock()

    def write(self, payload: dict[str, Any]) -> None:
        frame = encode_message(payload)
        with self._lock:
            self._stream.write(frame)
            self._stream.flush()
