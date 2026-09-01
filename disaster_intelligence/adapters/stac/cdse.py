from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from disaster_intelligence.adapters.stac.download import stream_download
from disaster_intelligence.adapters.stac.oauth import (
    cdse_access_token,
    earthdata_auth,
    earthdata_token,
)
from disaster_intelligence.adapters.stac.paginate import assert_host, paginate_stac_search
from disaster_intelligence.domain.errors import DisasterError, ValidationError
from disaster_intelligence.domain.ranking import rank_stac_features


def normalize_cdse_href(href: str) -> str:
    """Map CDSE STAC s3://eodata keys to the HTTPS object-store host."""
    if href.startswith("s3://eodata/"):
        return "https://eodata.dataspace.copernicus.eu/" + href[len("s3://eodata/") :]
    return href


class CdseStacAdapter:
    def __init__(
        self,
        search_url: str,
        cache_dir: Path,
        host_allowlist: list[str],
        cache_hours: float = 6.0,
        timeout_s: float = 90.0,
        collection_allowlist: list[str] | None = None,
        max_pages: int = 5,
        page_limit: int = 20,
    ) -> None:
        self._search_url = search_url
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._allow = set(host_allowlist)
        self._cache_hours = cache_hours
        self._timeout = timeout_s
        self._collections = set(collection_allowlist or [])
        self._max_pages = max(1, max_pages)
        self._page_limit = max(1, min(page_limit, 100))

    def _assert_host(self, url: str) -> None:
        assert_host(url, self._allow)

    def search(
        self,
        aoi: dict[str, Any],
        dt_start: str,
        dt_end: str | None,
        collections: list[str],
        max_cloud_pct: float | None = None,
    ) -> list[dict[str, Any]]:
        if self._collections:
            unknown = [c for c in collections if c not in self._collections]
            if unknown:
                raise ValidationError(f"STAC collections not allowlisted: {unknown}", "STAC_ERROR")
        geom = aoi
        if aoi.get("type") == "Feature":
            geom = aoi.get("geometry") or {}
        dt = dt_start if not dt_end else f"{dt_start}/{dt_end}"
        body = {
            "collections": collections,
            "intersects": geom,
            "datetime": dt,
            "limit": self._page_limit,
        }
        cache_key = hashlib.sha256(
            json.dumps({**body, "max_pages": self._max_pages}, sort_keys=True).encode()
        ).hexdigest()
        cache_path = self._cache_dir / f"{cache_key}.json"
        if cache_path.exists():
            age_h = (time.time() - cache_path.stat().st_mtime) / 3600.0
            if age_h <= self._cache_hours:
                return json.loads(cache_path.read_text(encoding="utf-8"))
        self._assert_host(self._search_url)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                features = paginate_stac_search(
                    client=client,
                    search_url=self._search_url,
                    body=body,
                    allow=self._allow,
                    max_pages=self._max_pages,
                )
        except httpx.HTTPError as exc:
            raise DisasterError(f"STAC search unreachable: {exc}", "STAC_ERROR") from exc
        if max_cloud_pct is not None:
            filtered = []
            for feat in features:
                props = feat.get("properties") or {}
                cloud = props.get("eo:cloud_cover")
                if cloud is None or float(cloud) <= max_cloud_pct:
                    filtered.append(feat)
            features = filtered
        ranked = rank_stac_features(features)
        cache_path.write_text(json.dumps(ranked), encoding="utf-8")
        return ranked

    def download(self, href: str, dest_uri: str) -> str:
        href = normalize_cdse_href(href)
        self._assert_host(href)
        dest = Path(dest_uri)
        dest.parent.mkdir(parents=True, exist_ok=True)
        headers: dict[str, str] = {}
        auth = None
        host = (urlparse(href).hostname or "").lower()
        if host.endswith("nasa.gov") or host.endswith("usgs.gov") or "earthdata" in host:
            token = earthdata_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
            else:
                auth = earthdata_auth()
        else:
            token = cdse_access_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return stream_download(
            href=href,
            dest=dest,
            allow=self._allow,
            headers=headers,
            auth=auth,
            timeout_s=3600.0,
        )
