from __future__ import annotations

import os
import socket

from disaster_intelligence.domain.errors import ValidationError


def scan_bytes(payload: bytes) -> None:
    """Optional ClamAV INSTREAM scan. No-op unless CLAMAV_HOST is set."""
    host = os.environ.get("CLAMAV_HOST", "").strip()
    if not host:
        return
    port = int(os.environ.get("CLAMAV_PORT", "3310"))
    timeout = float(os.environ.get("CLAMAV_TIMEOUT_S", "5"))
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(b"zINSTREAM\0")
            view = memoryview(payload)
            offset = 0
            chunk = 2048
            while offset < len(view):
                part = view[offset : offset + chunk]
                sock.sendall(len(part).to_bytes(4, "big") + part.tobytes())
                offset += chunk
            sock.sendall((0).to_bytes(4, "big"))
            reply = sock.recv(4096).decode("utf-8", errors="replace")
    except OSError as exc:
        raise ValidationError(f"ClamAV unreachable: {exc}", "INTERNAL_ERROR") from exc
    if "FOUND" in reply.upper():
        raise ValidationError("Upload failed malware scan", "UNSUPPORTED_MEDIA")
