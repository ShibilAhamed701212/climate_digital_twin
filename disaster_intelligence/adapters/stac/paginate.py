from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from disaster_intelligence.domain.errors import DisasterError, ValidationError


def next_href(payload: dict[str, Any]) -> str | None:
    for link in payload.get("links") or []:
        if isinstance(link, dict) and link.get("rel") == "next" and link.get("href"):
            return str(link["href"])
    return None


def assert_host(url: str, allow: set[str]) -> None:
    host = urlparse(url).hostname or ""
    if host not in allow:
        raise ValidationError(f"STAC host '{host}' is not allowlisted", "STAC_ERROR")


def paginate_stac_search(
    *,
    client: httpx.Client,
    search_url: str,
    body: dict[str, Any],
    allow: set[str],
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    url: str | None = None
    method = "POST"
    pages = 0
    while pages < max_pages:
        pages += 1
        if url is None:
            resp = client.post(search_url, json=body)
        else:
            assert_host(url, allow)
            resp = client.request(method, url)
        if resp.status_code >= 400:
            raise DisasterError(f"STAC search failed with HTTP {resp.status_code}", "STAC_ERROR")
        payload = resp.json() if resp.content else {}
        features.extend(list(payload.get("features") or []))
        nxt = next_href(payload)
        if not nxt:
            break
        url = nxt
        method = "GET"
    return features
