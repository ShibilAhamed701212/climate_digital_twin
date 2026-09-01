from __future__ import annotations

from disaster_intelligence.domain.enums import MVP_TASKS, DisasterType
from disaster_intelligence.domain.errors import TaskNotEnabledError, ValidationError

KNOWN_DISASTER_TYPES = frozenset(
    {
        DisasterType.FLOOD.value,
        DisasterType.CYCLONE.value,
        DisasterType.EARTHQUAKE.value,
        DisasterType.LANDSLIDE.value,
        DisasterType.WILDFIRE.value,
        DisasterType.HEATWAVE.value,
        DisasterType.DROUGHT.value,
    }
)


def ensure_flood_mvp(disaster_type: str, non_flood_enabled: bool) -> None:
    if disaster_type not in KNOWN_DISASTER_TYPES:
        raise ValidationError(f"Unknown disaster type '{disaster_type}'")
    if disaster_type == DisasterType.FLOOD.value:
        return
    if not non_flood_enabled:
        raise TaskNotEnabledError(
            f"Disaster type '{disaster_type}' is framework-only "
            f"(FEATURE_NON_FLOOD=false); no scientific mapper is bundled"
        )


def validate_tasks(tasks: list[str]) -> list[str]:
    if not tasks:
        return list(MVP_TASKS)
    unknown = [t for t in tasks if t not in MVP_TASKS]
    if unknown:
        raise ValidationError(f"Unsupported tasks: {unknown}")
    return tasks


def aoi_within_bounds(aoi: dict, bounds: dict[str, float], allow_outside: bool) -> None:
    if allow_outside:
        return
    coords = _collect_coords(aoi)
    if not coords:
        raise ValidationError("AOI must be a GeoJSON Polygon or MultiPolygon")
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    if (
        min(lats) < bounds["min_lat"]
        or max(lats) > bounds["max_lat"]
        or min(lons) < bounds["min_lon"]
        or max(lons) > bounds["max_lon"]
    ):
        raise ValidationError(
            "AOI is outside the configured Karnataka region", "AOI_OUTSIDE_REGION"
        )


def _collect_coords(geom: dict) -> list[list[float]]:
    gtype = geom.get("type")
    if gtype == "Feature":
        return _collect_coords(geom.get("geometry") or {})
    if gtype == "Polygon":
        ring = (geom.get("coordinates") or [[]])[0]
        return [[float(p[0]), float(p[1])] for p in ring]
    if gtype == "MultiPolygon":
        out: list[list[float]] = []
        for poly in geom.get("coordinates") or []:
            ring = poly[0] if poly else []
            out.extend([[float(p[0]), float(p[1])] for p in ring])
        return out
    return []
