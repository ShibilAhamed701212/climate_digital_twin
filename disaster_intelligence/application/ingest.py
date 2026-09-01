from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from disaster_intelligence.adapters.storage.clamav import scan_bytes
from disaster_intelligence.application.container import AppContainer
from disaster_intelligence.config import data_dir, env_flag, env_str
from disaster_intelligence.domain.entities import DisasterEvent, Scene
from disaster_intelligence.domain.enums import Authenticity
from disaster_intelligence.domain.errors import (
    DisasterError,
    NotFoundError,
    TaskNotEnabledError,
    ValidationError,
)
from disaster_intelligence.domain.geotiff import validate_upload_bytes
from disaster_intelligence.domain.ids import ulid
from disaster_intelligence.domain.policies import aoi_within_bounds, ensure_flood_mvp
from disaster_intelligence.domain.s1_assets import select_generic_asset, select_s1_assets

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, container: AppContainer) -> None:
        self._c = container

    def create_event(
        self,
        disaster_type: str,
        aoi: dict[str, Any],
        t_start: str,
        name: str = "",
        location_ids: list[str] | None = None,
        t_end: str | None = None,
    ) -> DisasterEvent:
        ensure_flood_mvp(disaster_type, env_flag("FEATURE_NON_FLOOD", False))
        bounds = self._c.config.get("aoi_bounds") or {}
        aoi_within_bounds(aoi, bounds, bool(self._c.config.get("allow_outside_aoi")))
        event = DisasterEvent.create(
            disaster_type=disaster_type,
            aoi=aoi,
            t_start=t_start,
            name=name,
            location_ids=location_ids,
            t_end=t_end,
        )
        return self._c.events.create(event)

    def get(self, event_id: str) -> DisasterEvent:
        event = self._c.events.get(event_id)
        if event is None:
            raise NotFoundError(f"Event {event_id} not found")
        return event

    def list_events(
        self, limit: int, offset: int, disaster_type: str | None
    ) -> tuple[list[DisasterEvent], int]:
        return self._c.events.list_events(limit, offset, disaster_type)


class IngestService:
    def __init__(self, container: AppContainer) -> None:
        self._c = container

    def ingest_stac(
        self,
        event_id: str,
        collections: list[str],
        datetime_range: str,
        max_cloud_pct: float | None,
    ) -> dict[str, Any]:
        event = self._c.events.get(event_id)
        if event is None:
            raise NotFoundError(f"Event {event_id} not found")
        parts = datetime_range.split("/")
        dt_start = parts[0]
        dt_end = parts[1] if len(parts) > 1 else event.t_end
        items = self._c.stac.search(
            event.aoi, dt_start, dt_end, collections, max_cloud_pct=max_cloud_pct
        )
        scene_ids: list[str] = []
        pending: list[dict[str, Any]] = []
        sync_max = int((self._c.config.get("limits") or {}).get("stac_sync_max") or 5)
        for item in items:
            collection = str(item.get("collection") or "").lower()
            is_s1 = "sentinel-1" in collection or "s1grd" in collection
            plan: dict[str, str] | None = None
            href: str | None = None
            if is_s1:
                try:
                    plan = select_s1_assets(item)
                    href = plan.get("product") or plan.get("vv")
                except ValidationError as exc:
                    logger.warning("S1 STAC item skipped for download: %s", exc)
                    href = None
            else:
                href = select_generic_asset(item)
            scene = _scene_from_stac_item(event_id, event.t_start, item, href)
            self._c.scenes.upsert(scene)
            scene_ids.append(scene.scene_id)
            if (
                _download_credentials_present()
                and href
                and href.startswith("http")
                and len(pending) < sync_max
            ):
                dest = self._c.rasters.path_for(f"{scene.scene_id}.tif")
                pending.append(
                    {
                        "scene": scene,
                        "href": href,
                        "dest": dest,
                        "plan": plan or {},
                        "s1": is_s1,
                        "aoi_bounds": _bounds_from_aoi(event.aoi),
                    }
                )
        if pending:
            workers = min(3, len(pending))

            def _one(row: dict[str, Any]) -> None:
                scene = row["scene"]
                try:
                    self._download_scene_assets(scene, row)
                except DisasterError as exc:
                    logger.warning("STAC download skipped for %s: %s", scene.scene_id, exc)

            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(_one, row) for row in pending]
                for fut in as_completed(futs):
                    fut.result()
        return {"ingest_id": ulid(), "scene_ids": scene_ids, "status": "completed"}

    def _download_scene_assets(self, scene: Scene, row: dict[str, Any]) -> None:
        from disaster_intelligence.domain.geotiff import write_float32_vv_vh
        from disaster_intelligence.preprocessing.sentinel1 import (
            extract_s1_measurements,
            write_s1_sidecar,
        )

        plan = row.get("plan") or {}
        dest = str(row["dest"])
        if row.get("s1") and plan.get("mode") == "dual":
            from disaster_intelligence.preprocessing.sentinel1 import window_vv_vh_to_aoi

            vv_dest = dest.replace(".tif", "_vv.tif")
            vh_dest = dest.replace(".tif", "_vh.tif")
            if not Path(vv_dest).is_file() or Path(vv_dest).stat().st_size == 0:
                self._c.stac.download(str(plan["vv"]), vv_dest)
            if not Path(vh_dest).is_file() or Path(vh_dest).stat().st_size == 0:
                self._c.stac.download(str(plan["vh"]), vh_dest)
            sidecar = Path(dest).with_suffix(".s1.json")
            try:
                max_pixels = int((self._c.config.get("limits") or {}).get("max_pixels") or 16_000_000)
                max_side = min(3500, int(max_pixels**0.5))
                aoi_bounds = row.get("aoi_bounds") or scene.bounds
                if not aoi_bounds:
                    raise ValidationError("AOI bounds missing for S1 window", "INVALID_GEOTIFF")
                stacked = window_vv_vh_to_aoi(vv_dest, vh_dest, aoi_bounds, max_side=max_side)
                bounds = stacked.bounds
                stack_path = Path(dest.replace(".tif", "_stack.tif"))
                write_float32_vv_vh(
                    stack_path,
                    stacked.vv,
                    stacked.vh,
                    west=bounds.get("west", 0.0),
                    north=bounds.get("north", 0.0),
                    xres=(bounds.get("east", 1.0) - bounds.get("west", 0.0))
                    / max(stacked.width, 1),
                    yres=(bounds.get("north", 1.0) - bounds.get("south", 0.0))
                    / max(stacked.height, 1),
                )
                scene.local_uri = write_s1_sidecar(sidecar, stack_path, bounds)
                scene.bounds = bounds
            except (TaskNotEnabledError, ValidationError, OSError) as exc:
                logger.warning("Could not stack dual S1 assets: %s", exc)
                scene.stac_href = str(plan.get("vv"))
                scene.local_uri = dest
            scene.checksum_sha256 = hashlib.sha256(Path(vv_dest).read_bytes()[:65536]).hexdigest()
            self._c.scenes.upsert(scene)
            return
        href = str(row["href"])
        dest_path = Path(dest)
        zip_existing = dest_path.with_suffix(".zip")
        if zip_existing.is_file() and zip_existing.stat().st_size > 0:
            dest_path = zip_existing
            digest = scene.checksum_sha256 or ""
        elif dest_path.is_file() and dest_path.stat().st_size > 0:
            digest = scene.checksum_sha256 or ""
        else:
            digest = self._c.stac.download(href, dest)
            dest_path = Path(dest)
        scene.checksum_sha256 = digest or scene.checksum_sha256
        if row.get("s1") and dest_path.suffix.lower() != ".zip":
            # PRODUCT downloads are often zip/octet-stream saved as .tif
            magic = dest_path.read_bytes()[:4]
            if magic.startswith(b"PK"):
                zip_path = dest_path.with_suffix(".zip")
                dest_path.replace(zip_path)
                dest_path = zip_path
        if dest_path.suffix.lower() == ".zip" or dest_path.read_bytes()[:2] == b"PK":
            try:
                from disaster_intelligence.preprocessing.sentinel1 import window_vv_vh_to_aoi

                meas_dir = dest_path.with_suffix("") / "meas"
                found: dict[str, Path] = {}
                for pol in ("vv", "vh"):
                    for ext in (".tiff", ".tif"):
                        cand = meas_dir / f"{pol}{ext}"
                        if cand.is_file() and cand.stat().st_size > 0:
                            found[pol] = cand
                            break
                if "vv" in found and "vh" in found:
                    vv_p, vh_p = found["vv"], found["vh"]
                else:
                    vv_p, vh_p = extract_s1_measurements(dest_path, meas_dir)
                max_pixels = int((self._c.config.get("limits") or {}).get("max_pixels") or 16_000_000)
                max_side = min(3500, int(max_pixels**0.5))
                aoi_bounds = row.get("aoi_bounds") or scene.bounds
                if not aoi_bounds:
                    raise ValidationError("AOI bounds missing for S1 window", "INVALID_GEOTIFF")
                stacked = window_vv_vh_to_aoi(vv_p, vh_p, aoi_bounds, max_side=max_side)
                stack_path = Path(dest.replace(".tif", "_stack.tif"))
                write_float32_vv_vh(
                    stack_path,
                    stacked.vv,
                    stacked.vh,
                    west=stacked.bounds.get("west", 0.0),
                    north=stacked.bounds.get("north", 0.0),
                    xres=(stacked.bounds.get("east", 1.0) - stacked.bounds.get("west", 0.0))
                    / max(stacked.width, 1),
                    yres=(stacked.bounds.get("north", 1.0) - stacked.bounds.get("south", 0.0))
                    / max(stacked.height, 1),
                )
                sidecar = Path(dest).with_suffix(".s1.json")
                scene.local_uri = write_s1_sidecar(sidecar, stack_path, stacked.bounds)
                scene.bounds = stacked.bounds
                self._c.scenes.upsert(scene)
                return
            except (ValidationError, TaskNotEnabledError) as exc:
                logger.warning("S1 zip could not be stacked: %s", exc)
        scene.local_uri = str(dest_path)
        self._c.scenes.upsert(scene)

    def upload_scene(self, event_id: str, filename: str, data: bytes, license_name: str) -> Scene:
        event = self._c.events.get(event_id)
        if event is None:
            raise NotFoundError(f"Event {event_id} not found")
        if not license_name:
            raise ValidationError("license is required")
        max_mb = int((self._c.config.get("limits") or {}).get("max_upload_mb") or 256)
        validate_upload_bytes(data, filename, max_mb * 1024 * 1024)
        scan_bytes(data)
        _assert_quota(len(data), self._c.config)
        digest = hashlib.sha256(data).hexdigest()
        for existing in self._c.scenes.list_for_event(event_id):
            if existing.checksum_sha256 == digest:
                return existing
        scene_id = ulid()
        provider, product = _provider_from_filename(filename)
        uri = self._c.rasters.put_bytes(f"{scene_id}.tif", data)
        scene = Scene(
            scene_id=scene_id,
            provider=provider,
            acquired_at=event.t_start,
            license=license_name,
            authenticity=Authenticity.USER_UPLOAD.value,
            event_id=event_id,
            product=product,
            local_uri=uri,
            checksum_sha256=digest,
            bounds=_bounds_from_aoi(event.aoi),
        )
        scene = self._c.scenes.upsert(scene)
        self._c.metrics["disaster_uploads_total"] = (
            int(self._c.metrics.get("disaster_uploads_total") or 0) + 1
        )
        return scene

    def ingest_drop(self, event_id: str, license_name: str = "user-drop") -> dict[str, Any]:
        inbox = data_dir() / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        scene_ids: list[str] = []
        for path in sorted(inbox.iterdir()):
            if path.suffix.lower() not in {".tif", ".tiff", ".cog"}:
                continue
            scene = self.upload_scene(event_id, path.name, path.read_bytes(), license_name)
            scene_ids.append(scene.scene_id)
        return {"ingest_id": ulid(), "scene_ids": scene_ids, "status": "completed"}


def _bounds_from_aoi(aoi: dict[str, Any]) -> dict[str, float]:
    geom: dict[str, Any]
    raw = aoi.get("geometry") if aoi.get("type") == "Feature" else aoi
    geom = raw if isinstance(raw, dict) else {}
    coords: list[list[float]] = []
    if geom.get("type") == "Polygon":
        coords = (geom.get("coordinates") or [[]])[0]
    elif geom.get("type") == "MultiPolygon":
        coords = ((geom.get("coordinates") or [[[]]])[0] or [[]])[0]
    if not coords:
        raise ValidationError("AOI geometry has no coordinates")
    lons = [float(p[0]) for p in coords]
    lats = [float(p[1]) for p in coords]
    return {"west": min(lons), "east": max(lons), "south": min(lats), "north": max(lats)}


def _assert_quota(extra_bytes: int, config: dict[str, Any]) -> None:
    max_mb = int((config.get("limits") or {}).get("max_storage_mb") or 20480)
    root = data_dir()
    used = extra_bytes
    for path in root.rglob("*"):
        if path.is_file():
            used += path.stat().st_size
            if used > max_mb * 1024 * 1024:
                raise ValidationError("Data directory quota exceeded", "PAYLOAD_TOO_LARGE")


def _download_credentials_present() -> bool:
    return bool(
        (env_str("CDSE_USERNAME") and env_str("CDSE_PASSWORD"))
        or (env_str("EARTHDATA_USERNAME") and env_str("EARTHDATA_PASSWORD"))
        or env_str("EARTHDATA_TOKEN")
    )


def _scene_from_stac_item(
    event_id: str, fallback_time: str, item: dict[str, Any], href: object
) -> Scene:
    props = item.get("properties") or {}
    collection = str(item.get("collection") or "")
    provider = _provider_from_stac(collection, str(props.get("platform") or ""))
    polar = props.get("sar:polarizations") or props.get("polarisation")
    if isinstance(polar, list):
        polar_s = ",".join(str(p) for p in polar)
    else:
        polar_s = str(polar) if polar else ""
    orbit = str(props.get("sat:orbit_state") or props.get("orbit") or "")
    platform = str(props.get("platform") or "")
    extras = [platform]
    if polar_s:
        extras.append(f"pol={polar_s}")
    if orbit:
        extras.append(f"orbit={orbit}")
    cloud = props.get("eo:cloud_cover")
    cloud_pct = float(cloud) if cloud is not None else None
    return Scene(
        scene_id=ulid(),
        provider=provider,
        acquired_at=str(props.get("datetime") or fallback_time),
        license="copernicus-open",
        authenticity=Authenticity.REAL.value,
        event_id=event_id,
        platform=" ".join(part for part in extras if part),
        product=collection,
        cloud_pct=cloud_pct,
        stac_href=href if isinstance(href, str) and href.startswith("http") else None,
    )


def _provider_from_stac(collection: str, platform: str) -> str:
    blob = f"{collection} {platform}".lower()
    if "sentinel-1" in blob or "s1grd" in blob:
        return "sentinel-1"
    if "sentinel-2" in blob:
        return "sentinel-2"
    if "nasadem" in blob:
        return "nasadem"
    if "landsat" in blob:
        return "landsat"
    return collection or "stac"


def _provider_from_filename(filename: str) -> tuple[str, str]:
    lower = filename.lower()
    if "nasadem" in lower or "srtm" in lower:
        return "nasadem", "elevation"
    if "worldpop" in lower or "population" in lower:
        return "worldpop", "population"
    if "landsat" in lower:
        return "landsat", "l2"
    if "s1" in lower or "sentinel-1" in lower or "grd" in lower:
        return "sentinel-1", "grd"
    if "s2" in lower or "sentinel-2" in lower:
        return "sentinel-2", "l2a"
    return "user", "upload"
