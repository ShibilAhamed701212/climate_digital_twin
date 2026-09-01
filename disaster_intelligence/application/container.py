from __future__ import annotations

from pathlib import Path
from typing import Any

from disaster_intelligence.adapters.http.twin_pointer import (
    HttpTwinPointerAdapter,
    NullTwinPointerAdapter,
)
from disaster_intelligence.adapters.osm.geojson_osm import GeojsonOsmAdapter
from disaster_intelligence.adapters.stac.cdse import CdseStacAdapter
from disaster_intelligence.adapters.stac.failover import FailoverStacAdapter
from disaster_intelligence.adapters.storage.raster_store import FilesystemRasterStore
from disaster_intelligence.adapters.storage.repositories import (
    JsonlAssessmentRepository,
    JsonlEventRepository,
    JsonlJobRepository,
    JsonlSceneRepository,
)
from disaster_intelligence.adapters.storage.vector_store import JsonVectorStore
from disaster_intelligence.config import data_dir, env_flag, env_str, load_disaster_config
from disaster_intelligence.inference.factory import create_flood_runner
from disaster_intelligence.ports.ports import StacPort, TwinPointerPort


def make_stac_adapter(cfg: dict[str, Any], root: Path, provider: str) -> CdseStacAdapter:
    stac_cfg = cfg.get("stac") or {}
    name = provider.lower()
    if name == "cmr":
        search_url = str(
            stac_cfg.get("cmr_search_url") or "https://cmr.earthdata.nasa.gov/stac/ASF/search"
        )
        host_allowlist = list(
            stac_cfg.get("cmr_host_allowlist")
            or [
                "cmr.earthdata.nasa.gov",
                "datapool.asf.alaska.edu",
                "e4ftl01.cr.usgs.gov",
                "data.lpdaac.earthdatacloud.nasa.gov",
            ]
        )
        collections = list(stac_cfg.get("cmr_collections") or stac_cfg.get("collections") or [])
    elif name == "mpc":
        search_url = str(
            stac_cfg.get("mpc_search_url")
            or "https://planetarycomputer.microsoft.com/api/stac/v1/search"
        )
        host_allowlist = list(
            stac_cfg.get("mpc_host_allowlist")
            or [
                "planetarycomputer.microsoft.com",
                "sentinel2l2a01.blob.core.windows.net",
                "sentinel1euwestrtc.blob.core.windows.net",
            ]
        )
        collections = list(stac_cfg.get("mpc_collections") or [])
    else:
        search_url = str(stac_cfg.get("search_url") or "")
        host_allowlist = list(stac_cfg.get("host_allowlist") or [])
        extra = [
            "identity.dataspace.copernicus.eu",
            "zipper.dataspace.copernicus.eu",
            "eodata.dataspace.copernicus.eu",
        ]
        for host in extra:
            if host not in host_allowlist:
                host_allowlist.append(host)
        collections = list(stac_cfg.get("collections") or [])
    return CdseStacAdapter(
        search_url=search_url,
        cache_dir=root / "tmp" / "stac_cache" / name,
        host_allowlist=host_allowlist,
        cache_hours=float(cfg.get("stac_cache_hours") or 6),
        collection_allowlist=collections,
        max_pages=int(stac_cfg.get("max_pages") or 5),
        page_limit=int(stac_cfg.get("page_limit") or 20),
    )


class AppContainer:
    def __init__(self) -> None:
        cfg = load_disaster_config()
        root = data_dir()
        jsonl = root / "jsonl"
        self.config = cfg
        self.events = JsonlEventRepository(jsonl / "events.jsonl")
        self.jobs = JsonlJobRepository(jsonl / "jobs.jsonl")
        self.scenes = JsonlSceneRepository(jsonl / "scenes.jsonl")
        self.assessments = JsonlAssessmentRepository(
            jsonl / "assessments.jsonl", jsonl / "location_index.jsonl"
        )
        self.rasters = FilesystemRasterStore(root / "cogs")
        self.vectors = JsonVectorStore(root / "geojson")
        provider = env_str(
            "STAC_PROVIDER", str((cfg.get("stac") or {}).get("provider") or "cdse")
        ).lower()
        primary = make_stac_adapter(cfg, root, provider)
        if env_flag("STAC_FAILOVER", False):
            backup_name = "mpc" if provider != "mpc" else "cdse"
            self.stac: StacPort = FailoverStacAdapter(
                [primary, make_stac_adapter(cfg, root, backup_name)]
            )
        else:
            self.stac = primary
        osm_path = str((cfg.get("osm") or {}).get("extract_path") or "data/osm/karnataka.geojson")
        self.osm = GeojsonOsmAdapter(osm_path)
        if env_flag("TWIN_POINTER_ENABLED", True):
            twin_url = env_str("TWIN_SERVICE_URL", "http://localhost:8001")
            self.twin_pointer: TwinPointerPort = HttpTwinPointerAdapter(twin_url)
        else:
            self.twin_pointer = NullTwinPointerAdapter()
        flood_cfg = cfg.get("flood_threshold") or {}
        self.flood_runner = create_flood_runner(
            env_str("MODEL_FLOOD", "threshold"),
            dn_max=int(flood_cfg.get("dn_max") or 80),
        )
        self.job_lock_held = False
        self.metrics: dict[str, Any] = {
            "disaster_jobs_total": {"queued": 0, "running": 0, "completed": 0, "failed": 0},
            "disaster_inflight_jobs": 0,
            "disaster_uploads_total": 0,
            "disaster_assessments_total": 0,
        }

    def bump_job_metric(self, status: str) -> None:
        totals = self.metrics["disaster_jobs_total"]
        if isinstance(totals, dict):
            totals[status] = int(totals.get(status, 0)) + 1


_CONTAINER: AppContainer | None = None


def get_container() -> AppContainer:
    global _CONTAINER
    if _CONTAINER is None:
        _CONTAINER = AppContainer()
    return _CONTAINER


def reset_container() -> None:
    global _CONTAINER
    _CONTAINER = None
