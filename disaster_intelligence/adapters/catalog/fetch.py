from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import httpx

from disaster_intelligence.domain.errors import DisasterError, ValidationError

ALLOWED_FETCH_HOSTS = frozenset(
    {
        "data.worldpop.org",
        "e4ftl01.cr.usgs.gov",
        "data.lpdaac.earthdatacloud.nasa.gov",
    }
)


def download_allowlisted(
    url: str,
    dest: Path,
    *,
    extra_hosts: frozenset[str] | None = None,
    headers: dict[str, str] | None = None,
    auth: tuple[str, str] | None = None,
    timeout_s: float = 120.0,
) -> str:
    host = urlparse(url).hostname or ""
    allow = ALLOWED_FETCH_HOSTS | (extra_hosts or frozenset())
    if host not in allow:
        raise ValidationError(f"Catalog host '{host}' is not allowlisted", "STAC_ERROR")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        resp = client.get(url, headers=headers or {}, auth=auth)
        if resp.status_code >= 400:
            raise DisasterError(f"Catalog download HTTP {resp.status_code}", "STAC_ERROR")
        payload = resp.content
    dest.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    dest.with_suffix(dest.suffix + ".sha256").write_text(digest, encoding="utf-8")
    return digest
