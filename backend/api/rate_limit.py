from __future__ import annotations

import os
import socket
import time
from urllib.parse import urlparse

_WINDOW_S = 60
_memory: dict[str, tuple[float, int]] = {}


def take_token(key: str, limit: int, window_s: int = _WINDOW_S) -> tuple[bool, int, int]:
    """Return (allowed, retry_after_seconds, remaining). Redis when RATE_LIMIT_REDIS_URL is set."""
    redis_url = os.environ.get("RATE_LIMIT_REDIS_URL", "").strip()
    if redis_url:
        counted = _redis_incr(redis_url, key, window_s)
        if counted is not None:
            remaining = max(0, limit - counted)
            if counted > limit:
                return False, window_s, remaining
            return True, 0, remaining
    return _memory_take(key, limit, window_s)


def _memory_take(key: str, limit: int, window_s: int) -> tuple[bool, int, int]:
    now = time.monotonic()
    start, count = _memory.get(key, (now, 0))
    if now - start > window_s:
        start, count = now, 0
    if count >= limit:
        return False, max(1, int(window_s - (now - start))), 0
    count += 1
    _memory[key] = (start, count)
    if len(_memory) > 10_000:
        expired = [k for k, (s, _) in _memory.items() if now - s > window_s]
        for k in expired:
            _memory.pop(k, None)
    return True, 0, max(0, limit - count)


def reset_memory_limiter() -> None:
    _memory.clear()


def _redis_incr(url: str, key: str, ttl_s: int) -> int | None:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=0.05) as sock:
            sock.sendall(_resp_array(["INCR", key]))
            incr_line = _read_line(sock)
            if not incr_line.startswith(":"):
                return None
            value = int(incr_line[1:])
            if value == 1:
                sock.sendall(_resp_array(["EXPIRE", key, str(ttl_s)]))
                _read_line(sock)
            return value
    except (OSError, ValueError, TimeoutError):
        return None


def _resp_array(parts: list[str]) -> bytes:
    chunks = [f"*{len(parts)}\r\n".encode()]
    for part in parts:
        payload = part.encode()
        chunks.append(f"${len(payload)}\r\n".encode() + payload + b"\r\n")
    return b"".join(chunks)


def _read_line(sock: socket.socket) -> str:
    buf = b""
    while not buf.endswith(b"\r\n"):
        chunk = sock.recv(1)
        if not chunk:
            break
        buf += chunk
        if len(buf) > 64:
            break
    return buf.decode("ascii", errors="replace").strip()
