from __future__ import annotations

import logging
from typing import Any

from disaster_intelligence.domain.errors import DisasterError
from disaster_intelligence.ports.ports import StacPort

logger = logging.getLogger(__name__)


class FailoverStacAdapter:
    """Try adapters in order; first successful search wins. Download uses the first adapter."""

    def __init__(self, adapters: list[StacPort]) -> None:
        if not adapters:
            raise DisasterError("No STAC adapters configured", "STAC_ERROR")
        self._adapters = adapters

    def search(
        self,
        aoi: dict[str, Any],
        dt_start: str,
        dt_end: str | None,
        collections: list[str],
        max_cloud_pct: float | None = None,
    ) -> list[dict[str, Any]]:
        last: DisasterError | None = None
        for adapter in self._adapters:
            try:
                return adapter.search(aoi, dt_start, dt_end, collections, max_cloud_pct)
            except DisasterError as exc:
                last = exc
                logger.warning("STAC adapter failed, trying next: %s", exc)
        raise last or DisasterError("STAC search failed", "STAC_ERROR")

    def download(self, href: str, dest_uri: str) -> str:
        last: DisasterError | None = None
        for adapter in self._adapters:
            try:
                return adapter.download(href, dest_uri)
            except DisasterError as exc:
                last = exc
                logger.warning("STAC download adapter failed, trying next: %s", exc)
        raise last or DisasterError("STAC download failed", "STAC_ERROR")
