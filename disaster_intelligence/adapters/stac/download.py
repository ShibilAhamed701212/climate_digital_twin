from __future__ import annotations

import hashlib
import time
from pathlib import Path

import httpx

from disaster_intelligence.adapters.stac.paginate import assert_host
from disaster_intelligence.domain.errors import DisasterError


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def stream_download(
    *,
    href: str,
    dest: Path,
    allow: set[str],
    headers: dict[str, str] | None = None,
    auth: tuple[str, str] | None = None,
    timeout_s: float = 120.0,
) -> str:
    """Download with optional Range resume into dest.part, then verify sha256 sidecar."""
    assert_host(href, allow)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    existing = part.stat().st_size if part.exists() else 0
    req_headers = dict(headers or {})
    req_headers.setdefault("User-Agent", "climate-digital-twin-die/2.1")
    if existing:
        req_headers["Range"] = f"bytes={existing}-"
    last_error: Exception | None = None
    for delay in (1.0, 4.0, 16.0):
        try:
            with (
                httpx.Client(timeout=timeout_s, follow_redirects=True) as client,
                client.stream("GET", href, headers=req_headers, auth=auth) as resp,
            ):
                if resp.status_code in {429, 500, 502, 503}:
                    time.sleep(delay)
                    continue
                if existing and resp.status_code == 200:
                    existing = 0
                    part.unlink(missing_ok=True)
                elif resp.status_code not in {200, 206}:
                    raise DisasterError(f"STAC download HTTP {resp.status_code}", "STAC_ERROR")
                mode = "ab" if existing and resp.status_code == 206 else "wb"
                with part.open(mode) as fh:
                    for chunk in resp.iter_bytes(1024 * 1024):
                        fh.write(chunk)
            part.replace(dest)
            digest = sha256_file(dest)
            dest.with_suffix(dest.suffix + ".sha256").write_text(digest, encoding="utf-8")
            return digest
        except httpx.HTTPError as exc:
            last_error = exc
            time.sleep(delay)
    raise DisasterError(f"STAC download failed: {last_error}", "STAC_ERROR")
