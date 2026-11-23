"""
Xoose–LoveYou Native Messaging Host (com.xoose.loveyou.host).

Di-spawn oleh Google Chrome, Microsoft Edge, atau Mozilla Firefox melalui
WebExtensions Native Messaging (stdin/stdout 32-bit length-prefixed JSON).

Jaminan Keamanan:
- stdout EKSKLUSIF untuk protokol Native Messaging; seluruh log ditulis ke stderr & file log.
- Tidak menerima perintah shell atau path output arbitrer dari extension.
- Berkomunikasi dengan LoveYou Agent melalui direktori bridge user-scoped
  (%LOCALAPPDATA%/XooseLoveYouAgent/bridge) dengan atomic rename (tanpa membuka port HTTP).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, BinaryIO

# Pastikan modul lokal native-host dapat diimpor baik langsung maupun dari PyInstaller
_HOST_DIR = Path(__file__).resolve().parent
if str(_HOST_DIR) not in sys.path:
    sys.path.insert(0, str(_HOST_DIR))

from image_assembler import AssemblyError, ImageAssembler
from protocol import NativeStreamWriter, ProtocolError, configure_binary_stdio, read_message

HOST_VERSION = "1.0.0"
PROTOCOL_VERSION = 1


def default_bridge_dir() -> Path:
    override = os.environ.get("XOOSE_BRIDGE_DIR", "").strip()
    if override:
        return Path(override).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return (Path(local_app_data) / "XooseLoveYouAgent" / "bridge").resolve()


def setup_logger(bridge_dir: Path) -> logging.Logger:
    """Mengonfigurasi logger hanya ke stderr dan file log — TIDAK PERNAH ke stdout."""
    logger = logging.getLogger("xoose.native_host")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    try:
        logs_dir = bridge_dir.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            logs_dir / "native-host.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass

    return logger


def atomic_write_json(target_path: Path, data: dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(target_path.suffix + f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    last_err: Exception | None = None
    for attempt in range(6):
        try:
            os.replace(tmp_path, target_path)
            return
        except PermissionError as exc:
            last_err = exc
            time.sleep(0.03 * (attempt + 1))
    tmp_path.unlink(missing_ok=True)
    if last_err is not None:
        raise last_err


class NativeMessagingHost:
    """Loop utama Native Messaging Host yang dapat dijalankan via stdin/stdout atau diuji in-memory."""

    def __init__(
        self,
        in_stream: BinaryIO,
        out_stream: BinaryIO,
        bridge_dir: str | Path | None = None,
        watch_interval_seconds: float = 1.0,
        logger: logging.Logger | None = None,
    ):
        self.in_stream = in_stream
        self.writer = NativeStreamWriter(out_stream)
        self.bridge_dir = Path(bridge_dir).resolve() if bridge_dir else default_bridge_dir()
        self.bridge_dir.mkdir(parents=True, exist_ok=True)

        self.runtime_config_file = self.bridge_dir / "runtime_config.json"
        self.control_signal_file = self.bridge_dir / "control_signal.json"
        self.spool_root = self.bridge_dir / "spool"

        self.logger = logger or setup_logger(self.bridge_dir)
        self.watch_interval_seconds = max(0.1, float(watch_interval_seconds))

        self.browser_name = "chrome"
        self.extension_id = ""
        self._last_pushed_config_signature: str = ""
        self._last_control_seq: int = 0
        self._device_id: str = ""

        self.assembler = ImageAssembler(
            spool_root=self.spool_root,
            device_id_fn=lambda: self._device_id,
        )

        self._stop_event = threading.Event()
        self._watcher_thread: threading.Thread | None = None

    def _read_runtime_config(self) -> dict[str, Any] | None:
        if not self.runtime_config_file.exists():
            return None
        try:
            data = json.loads(self.runtime_config_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if data.get("device_id"):
                    self._device_id = str(data["device_id"])
                return data
        except Exception as exc:
            self.logger.warning("Gagal membaca runtime_config.json: %s", exc)
        return None

    def _build_config_update_message(self, data: dict[str, Any] | None) -> dict[str, Any]:
        if not data:
            return {
                "type": "config_update",
                "config_version": 0,
                "active_source": "desktop_mss",
                "browser_capture": {
                    "enabled": False,
                    "capture_mode": "active_tab",
                    "permission_mode": "local_start",
                    "local_session_required": True,
                    "pause_when_browser_unfocused": True,
                    "pause_when_tab_inactive": True,
                    "image_format": "webp",
                    "fallback_format": "png",
                    "capture_interval_seconds": 10,
                    "rules": [],
                },
            }

        cfg = data.get("config", data)
        active_source = data.get("active_source") or cfg.get("capture_policy", {}).get("active_source", "desktop_mss")
        browser_capture = data.get("browser_capture") or cfg.get("browser_capture") or {
            "enabled": False,
            "capture_mode": "active_tab",
            "permission_mode": "local_start",
            "local_session_required": True,
            "pause_when_browser_unfocused": True,
            "pause_when_tab_inactive": True,
            "image_format": "webp",
            "fallback_format": "png",
            "capture_interval_seconds": 10,
            "rules": [],
        }

        return {
            "type": "config_update",
            "config_version": int(data.get("config_version", 0)),
            "active_source": active_source,
            "browser_capture": browser_capture,
        }

    def _check_bridge_updates(self, force_config: bool = False) -> None:
        raw_cfg = self._read_runtime_config()
        if raw_cfg is not None:
            sig = json.dumps(raw_cfg, sort_keys=True)
            if force_config or sig != self._last_pushed_config_signature:
                self._last_pushed_config_signature = sig
                self.writer.write(self._build_config_update_message(raw_cfg))
        elif force_config:
            self.writer.write(self._build_config_update_message(None))

        if self.control_signal_file.exists():
            try:
                sig_data = json.loads(self.control_signal_file.read_text(encoding="utf-8"))
                if isinstance(sig_data, dict):
                    seq = int(sig_data.get("seq", 0))
                    action = str(sig_data.get("action", "")).strip().lower()
                    if seq > self._last_control_seq and action in ("start", "pause", "resume", "stop", "sync_config"):
                        self._last_control_seq = seq
                        self.writer.write({
                            "type": "control_action",
                            "action": action,
                            "source": str(sig_data.get("source", "loveyou_agent")),
                            "seq": seq,
                        })
            except Exception as exc:
                self.logger.warning("Gagal membaca control_signal.json: %s", exc)

    def _watcher_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_bridge_updates(force_config=False)
                self.assembler.cleanup_expired()
            except Exception as exc:
                self.logger.warning("Watcher bridge error: %s", exc)
            self._stop_event.wait(timeout=self.watch_interval_seconds)

    def _write_host_status(self, status_payload: dict[str, Any]) -> None:
        browser = str(status_payload.get("browser") or self.browser_name or "chrome").strip().lower()
        if browser not in ("chrome", "edge", "firefox"):
            browser = "chrome"
        self.browser_name = browser

        record = dict(status_payload)
        record.pop("type", None)
        record["browser"] = browser
        record["extension_id"] = self.extension_id
        record["host_version"] = HOST_VERSION
        record["host_pid"] = os.getpid()
        record["updated_at"] = datetime.now(timezone.utc).isoformat()

        target = self.bridge_dir / f"host_status_{browser}.json"
        try:
            atomic_write_json(target, record)
        except Exception as exc:
            self.logger.warning("Gagal menulis %s: %s", target.name, exc)

    def handle_message(self, msg: dict[str, Any]) -> None:
        msg_type = msg["type"]

        if msg_type == "hello":
            browser = str(msg.get("browser", "chrome")).strip().lower()
            if browser in ("chrome", "edge", "firefox"):
                self.browser_name = browser
            self.extension_id = str(msg.get("extension_id", "")).strip()[:128]
            self.logger.info("Extension terhubung: browser=%s id=%s", self.browser_name, self.extension_id)
            self.writer.write({
                "type": "hello_ack",
                "protocol_version": PROTOCOL_VERSION,
                "host_version": HOST_VERSION,
                "spool_ready": True,
            })
            self._check_bridge_updates(force_config=True)
            return

        if msg_type == "ping":
            self.writer.write({
                "type": "pong",
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            return

        if msg_type == "get_config":
            raw_cfg = self._read_runtime_config()
            self.writer.write(self._build_config_update_message(raw_cfg))
            return

        if msg_type == "status_report":
            self._write_host_status(msg)
            return

        if msg_type == "capture_abort":
            cid = str(msg.get("capture_id", ""))
            self.assembler.abort(cid)
            self.logger.info("Capture dibatalkan: %s (reason=%s)", cid, msg.get("reason", ""))
            return

        if msg_type == "capture_chunk":
            try:
                res = self.assembler.add_chunk(msg)
                if res.get("completed"):
                    self.writer.write({
                        "type": "capture_ack",
                        "capture_id": res["capture_id"],
                        "status": "spooled",
                        "mime_type": res["mime_type"],
                        "image_checksum": res["image_checksum"],
                    })
                    self.logger.info(
                        "Capture berhasil di-spool: %s (%s, %d bytes)",
                        res["capture_id"],
                        res["mime_type"],
                        res["file_size_bytes"],
                    )
            except AssemblyError as exc:
                self.logger.warning("AssemblyError (%s): %s", exc.code, exc)
                self.writer.write({
                    "type": "capture_error",
                    "capture_id": exc.capture_id or str(msg.get("capture_id", "")),
                    "code": exc.code,
                    "message": str(exc),
                })

    def run(self, start_watcher: bool = True) -> None:
        if start_watcher:
            self._watcher_thread = threading.Thread(
                target=self._watcher_loop,
                daemon=True,
                name="NativeBridgeWatcher",
            )
            self._watcher_thread.start()

        try:
            while not self._stop_event.is_set():
                try:
                    msg = read_message(self.in_stream)
                except ProtocolError as exc:
                    self.logger.warning("ProtocolError (%s): %s", exc.code, exc)
                    try:
                        self.writer.write({
                            "type": "capture_error",
                            "capture_id": "",
                            "code": exc.code,
                            "message": str(exc),
                        })
                    except Exception:
                        pass
                    if exc.code in ("TRUNCATED_HEADER", "TRUNCATED_BODY", "MESSAGE_TOO_LARGE"):
                        break
                    continue

                if msg is None:
                    # EOF bersih saat browser menutup koneksi
                    break

                self.handle_message(msg)
        finally:
            self._stop_event.set()
            if self._watcher_thread and self._watcher_thread.is_alive():
                self._watcher_thread.join(timeout=1.5)
            # Tandai disconnected di status file saat host berhenti bersih
            self._write_host_status({
                "browser": self.browser_name,
                "extension_connected": False,
                "capture_state": "host_exited",
            })


def main() -> int:
    configure_binary_stdio()
    host = NativeMessagingHost(
        in_stream=sys.stdin.buffer,
        out_stream=sys.stdout.buffer,
    )
    host.run(start_watcher=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
