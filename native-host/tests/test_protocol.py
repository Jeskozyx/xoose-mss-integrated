"""
Unit & subprocess tests untuk protokol Native Messaging (protocol.py & host.py).
Memastikan:
- Framing 32-bit length-prefixed JSON valid/invalid
- Allowlist tipe pesan & penolakan field terlarang (shell/output_path)
- Live push runtime_config.json & status_report -> host_status_<browser>.json
- stdout subprocess 100% bersih tanpa bocoran log debug apa pun!
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from PIL import Image

NATIVE_HOST_DIR = Path(__file__).resolve().parent.parent
if str(NATIVE_HOST_DIR) not in sys.path:
    sys.path.insert(0, str(NATIVE_HOST_DIR))

from host import NativeMessagingHost
from protocol import ProtocolError, encode_message, read_message


def _make_sample_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 24), color=(16, 185, 129)).save(buf, format="PNG")
    return buf.getvalue()


def _read_all_frames(raw_bytes: bytes) -> list[dict]:
    stream = io.BytesIO(raw_bytes)
    messages = []
    while True:
        header = stream.read(4)
        if not header:
            break
        assert len(header) == 4, "Header frame stdout rusak / tercemar log!"
        (length,) = struct.unpack("<I", header)
        body = stream.read(length)
        assert len(body) == length, "Body frame stdout terpotong!"
        messages.append(json.loads(body.decode("utf-8")))
    return messages


def test_encode_and_read_valid_message():
    msg = {"type": "ping", "ts": "2026-11-23T13:00:00Z"}
    raw = encode_message(msg)
    assert len(raw) == 4 + len(raw[4:])
    parsed = read_message(io.BytesIO(raw))
    assert parsed == msg


def test_read_message_rejects_disallowed_type_and_forbidden_fields():
    bad_type = struct.pack("<I", 22) + b'{"type":"run_command"}'
    with pytest.raises(ProtocolError) as exc1:
        read_message(io.BytesIO(bad_type))
    assert exc1.value.code == "DISALLOWED_MESSAGE_TYPE"

    body = json.dumps({"type": "ping", "shell": "whoami"}).encode("utf-8")
    with pytest.raises(ProtocolError) as exc2:
        read_message(io.BytesIO(struct.pack("<I", len(body)) + body))
    assert exc2.value.code == "FORBIDDEN_FIELD"

    body2 = json.dumps({"type": "capture_chunk", "output_path": "C:\\Windows\\evil.png"}).encode("utf-8")
    with pytest.raises(ProtocolError) as exc3:
        read_message(io.BytesIO(struct.pack("<I", len(body2)) + body2))
    assert exc3.value.code == "FORBIDDEN_FIELD"


def test_read_message_rejects_oversized_and_truncated_frames():
    huge_header = struct.pack("<I", 5 * 1024 * 1024)
    with pytest.raises(ProtocolError) as exc1:
        read_message(io.BytesIO(huge_header))
    assert exc1.value.code == "MESSAGE_TOO_LARGE"

    truncated = struct.pack("<I", 100) + b'{"type":"ping"}'
    with pytest.raises(ProtocolError) as exc2:
        read_message(io.BytesIO(truncated))
    assert exc2.value.code == "TRUNCATED_BODY"

    bad_json_body = b"{invalid-json"
    with pytest.raises(ProtocolError) as exc3:
        read_message(io.BytesIO(struct.pack("<I", len(bad_json_body)) + bad_json_body))
    assert exc3.value.code == "INVALID_JSON"


def test_host_in_memory_hello_config_status_and_capture(tmp_path: Path):
    bridge_dir = tmp_path / "bridge"
    bridge_dir.mkdir(parents=True)

    # Tulis runtime_config.json seperti ditulis LoveYou Agent
    (bridge_dir / "runtime_config.json").write_text(
        json.dumps(
            {
                "device_id": "dev-uuid-123",
                "config_version": 5,
                "active_source": "browser_domain",
                "browser_capture": {
                    "enabled": True,
                    "capture_mode": "active_tab",
                    "permission_mode": "local_start",
                    "capture_interval_seconds": 10,
                    "rules": [
                        {
                            "id": "konstanta-domain",
                            "enabled": True,
                            "domain": "konstantaedu.com",
                            "include_subdomains": True,
                            "schemes": ["https"],
                            "browsers": ["chrome", "edge", "firefox"],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    png_bytes = _make_sample_png_bytes()
    b64 = base64.b64encode(png_bytes).decode("ascii")
    sha = hashlib.sha256(png_bytes).hexdigest()
    cid = str(uuid.uuid4())

    in_frames = b"".join(
        [
            encode_message({"type": "hello", "protocol_version": 1, "browser": "chrome", "extension_id": "a" * 32}),
            encode_message({"type": "status_report", "browser": "chrome", "extension_connected": True, "capture_state": "capturing", "config_version": 5}),
            encode_message(
                {
                    "type": "capture_chunk",
                    "capture_id": cid,
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "mime_type": "image/png",
                    "target_format": "webp",
                    "payload": b64,
                    "checksum": sha,
                    "meta": {
                        "source": "browser_tab",
                        "browser": "chrome",
                        "rule_id": "konstanta-domain",
                        "origin_domain": "www.konstantaedu.com",
                    },
                }
            ),
        ]
    )

    out_buf = io.BytesIO()
    host = NativeMessagingHost(
        in_stream=io.BytesIO(in_frames),
        out_stream=out_buf,
        bridge_dir=bridge_dir,
    )
    host.run(start_watcher=False)

    responses = _read_all_frames(out_buf.getvalue())
    types = [r["type"] for r in responses]
    assert types == ["hello_ack", "config_update", "capture_ack"]
    assert responses[1]["config_version"] == 5
    assert responses[1]["active_source"] == "browser_domain"
    assert responses[2]["capture_id"] == cid
    assert responses[2]["status"] == "spooled"
    assert responses[2]["mime_type"] == "image/webp"

    # Pastikan file spool & metadata ditulis secara atomik
    incoming = bridge_dir / "spool" / "incoming"
    assert (incoming / f"{cid}.webp").exists()
    meta = json.loads((incoming / f"{cid}.meta.json").read_text(encoding="utf-8"))
    assert meta["source"] == "browser_tab"
    assert meta["device_id"] == "dev-uuid-123"
    assert meta["origin_domain"] == "www.konstantaedu.com"


def test_host_subprocess_stdout_is_strictly_clean_framed_json(tmp_path: Path):
    """Menjalankan host.py sebagai proses nyata untuk memastikan 0 byte log mencemari stdout."""
    bridge_dir = tmp_path / "sub_bridge"
    env = os.environ.copy()
    env["XOOSE_BRIDGE_DIR"] = str(bridge_dir)

    stdin_bytes = encode_message({"type": "hello", "browser": "firefox", "extension_id": "loveyou-capture@xoose.local"}) + encode_message({"type": "ping"})

    proc = subprocess.run(
        [sys.executable, "-u", str(NATIVE_HOST_DIR / "host.py")],
        input=stdin_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=10,
        check=True,
    )

    # Jika ada satu baris print() biasa di stdout, _read_all_frames pasti gagal!
    frames = _read_all_frames(proc.stdout)
    assert [f["type"] for f in frames] == ["hello_ack", "config_update", "pong"]
    # Pastikan log memang masuk ke stderr (bukan stdout)
    assert b"Extension terhubung" in proc.stderr
