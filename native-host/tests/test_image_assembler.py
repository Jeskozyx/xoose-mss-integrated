"""
Unit tests untuk ImageAssembler (image_assembler.py):
- Multi-chunk transfer normal & urutan acak (out-of-order)
- Chunk hilang (incomplete) + pembersihan timeout
- Chunk duplikat ditolak
- Checksum SHA-256 salah ditolak
- Payload melebihi batas ukuran / chunk count ditolak
- Path traversal pada capture_id ditolak
- Host restart di tengah assembly (instance baru bersih dari state lama)
- Konversi WEBP sukses + atomic rename ke spool/incoming/
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import uuid
from pathlib import Path

import pytest
from PIL import Image

NATIVE_HOST_DIR = Path(__file__).resolve().parent.parent
if str(NATIVE_HOST_DIR) not in sys.path:
    sys.path.insert(0, str(NATIVE_HOST_DIR))

from image_assembler import AssemblyError, ImageAssembler


def _make_png(width: int = 64, height: int = 48) -> tuple[bytes, str, str]:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(59, 130, 246)).save(buf, format="PNG")
    raw = buf.getvalue()
    return raw, base64.b64encode(raw).decode("ascii"), hashlib.sha256(raw).hexdigest()


def _split_chunks(b64: str, count: int) -> list[str]:
    size = max(1, (len(b64) + count - 1) // count)
    parts = [b64[i : i + size] for i in range(0, len(b64), size)]
    return parts


def test_multichunk_out_of_order_assembly_and_webp_conversion(tmp_path: Path):
    assembler = ImageAssembler(spool_root=tmp_path / "spool", device_id_fn=lambda: "dev-01")
    _, b64, sha = _make_png(80, 60)
    parts = _split_chunks(b64, 3)
    assert len(parts) == 3
    cid = str(uuid.uuid4())

    # Kirim dengan urutan acak: index 2, 0, lalu 1
    r1 = assembler.add_chunk({
        "capture_id": cid, "chunk_index": 2, "chunk_count": 3,
        "mime_type": "image/png", "target_format": "webp", "payload": parts[2], "checksum": sha,
    })
    assert r1["completed"] is False

    r2 = assembler.add_chunk({
        "capture_id": cid, "chunk_index": 0, "chunk_count": 3,
        "mime_type": "image/png", "target_format": "webp", "payload": parts[0], "checksum": sha,
        "meta": {"browser": "edge", "rule_id": "r1", "origin_domain": "konstantaedu.com/secret?a=1"},
    })
    assert r2["completed"] is False

    r3 = assembler.add_chunk({
        "capture_id": cid, "chunk_index": 1, "chunk_count": 3,
        "mime_type": "image/png", "target_format": "webp", "payload": parts[1], "checksum": sha,
    })
    assert r3["completed"] is True
    assert r3["mime_type"] == "image/webp"
    assert r3["resolution"] == "80x60"
    assert Path(r3["image_path"]).exists()
    assert Path(r3["meta_path"]).exists()
    # Tidak ada file .tmp tertinggal
    assert list((tmp_path / "spool" / "tmp").glob("*")) == []
    # Sanitasi origin_domain (tanpa path/query)
    meta = json.loads(Path(r3["meta_path"]).read_text(encoding="utf-8"))
    assert meta["origin_domain"] == "konstantaedu.com"
    assert meta["browser"] == "edge"


def test_duplicate_chunk_rejected(tmp_path: Path):
    assembler = ImageAssembler(spool_root=tmp_path / "spool")
    _, b64, sha = _make_png()
    parts = _split_chunks(b64, 2)
    cid = str(uuid.uuid4())

    assembler.add_chunk({
        "capture_id": cid, "chunk_index": 0, "chunk_count": 2,
        "mime_type": "image/png", "payload": parts[0], "checksum": sha,
    })
    with pytest.raises(AssemblyError) as exc:
        assembler.add_chunk({
            "capture_id": cid, "chunk_index": 0, "chunk_count": 2,
            "mime_type": "image/png", "payload": parts[0], "checksum": sha,
        })
    assert exc.value.code == "DUPLICATE_CHUNK"


def test_wrong_checksum_rejected_and_no_spool_written(tmp_path: Path):
    assembler = ImageAssembler(spool_root=tmp_path / "spool")
    _, b64, _ = _make_png()
    cid = str(uuid.uuid4())
    wrong_sha = "0" * 64

    with pytest.raises(AssemblyError) as exc:
        assembler.add_chunk({
            "capture_id": cid, "chunk_index": 0, "chunk_count": 1,
            "mime_type": "image/png", "payload": b64, "checksum": wrong_sha,
        })
    assert exc.value.code == "CHECKSUM_MISMATCH"
    assert list((tmp_path / "spool" / "incoming").glob("*")) == []


def test_payload_exceeding_max_size_and_invalid_chunk_index_rejected(tmp_path: Path):
    assembler = ImageAssembler(spool_root=tmp_path / "spool", max_image_bytes=64)
    _, b64, sha = _make_png(128, 128)
    cid = str(uuid.uuid4())

    with pytest.raises(AssemblyError) as exc1:
        assembler.add_chunk({
            "capture_id": cid, "chunk_index": 0, "chunk_count": 1,
            "mime_type": "image/png", "payload": b64, "checksum": sha,
        })
    assert exc1.value.code == "PAYLOAD_TOO_LARGE"

    with pytest.raises(AssemblyError) as exc2:
        assembler.add_chunk({
            "capture_id": cid, "chunk_index": 5, "chunk_count": 2,
            "mime_type": "image/png", "payload": "AAAA", "checksum": sha,
        })
    assert exc2.value.code == "INVALID_CHUNK_INDEX"


def test_path_traversal_capture_id_rejected(tmp_path: Path):
    assembler = ImageAssembler(spool_root=tmp_path / "spool")
    _, b64, sha = _make_png()
    with pytest.raises(AssemblyError) as exc:
        assembler.add_chunk({
            "capture_id": "../../evil", "chunk_index": 0, "chunk_count": 1,
            "mime_type": "image/png", "payload": b64, "checksum": sha,
        })
    assert exc.value.code == "INVALID_CAPTURE_ID"


def test_missing_chunk_timeout_and_host_restart_recovery(tmp_path: Path):
    clock = [100.0]
    assembler1 = ImageAssembler(spool_root=tmp_path / "spool", timeout_seconds=30.0, now_fn=lambda: clock[0])
    _, b64, sha = _make_png()
    parts = _split_chunks(b64, 2)
    cid = str(uuid.uuid4())

    # Hanya chunk 0 dikirim, chunk 1 hilang
    assembler1.add_chunk({
        "capture_id": cid, "chunk_index": 0, "chunk_count": 2,
        "mime_type": "image/png", "payload": parts[0], "checksum": sha,
    })
    assert assembler1.pending_count() == 1

    # Lewat 35 detik -> cleanup membersihkan sesi incomplete
    clock[0] += 35.0
    expired = assembler1.cleanup_expired()
    assert cid in expired
    assert assembler1.pending_count() == 0

    # Simulasikan host restart (instance baru) menerima capture baru dengan sukses
    assembler2 = ImageAssembler(spool_root=tmp_path / "spool")
    cid2 = str(uuid.uuid4())
    res = assembler2.add_chunk({
        "capture_id": cid2, "chunk_index": 0, "chunk_count": 1,
        "mime_type": "image/png", "payload": b64, "checksum": sha,
    })
    assert res["completed"] is True
    assert Path(res["image_path"]).exists()
