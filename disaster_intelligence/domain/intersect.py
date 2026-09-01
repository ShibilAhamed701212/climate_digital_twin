from __future__ import annotations

from typing import Any

from disaster_intelligence.domain.enums import DamageClass, QualityFlag
from disaster_intelligence.domain.zonal import geometry_centroid, pixel_water


def _line_in_water(geom: dict[str, Any], mask: list[list[int]], bounds: dict[str, float]) -> bool:
    coords: list[Any]
    if geom.get("type") == "LineString":
        coords = list(geom.get("coordinates") or [])
    else:
        coords = [pt for part in (geom.get("coordinates") or []) for pt in part]
    for pt in coords:
        if (
            isinstance(pt, list)
            and len(pt) >= 2
            and pixel_water(float(pt[0]), float(pt[1]), mask, bounds)
        ):
            return True
    return False


def _amenity_in_water(
    geom: dict[str, Any], mask: list[list[int]], bounds: dict[str, float]
) -> bool:
    centroid = geometry_centroid(geom)
    if centroid is None:
        return False
    return pixel_water(centroid[0], centroid[1], mask, bounds)


def intersect_osm(
    features: list[dict[str, Any]],
    mask: list[list[int]],
    bounds: dict[str, float],
    *,
    area_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Mark OSM features in water. Polygons use sampled area; points use centroid."""
    from disaster_intelligence.domain.zonal import flood_fraction_for_polygon

    out: list[dict[str, Any]] = []
    for feat in features:
        geom = feat.get("geometry") or {}
        props = dict(feat.get("properties") or {})
        gtype = geom.get("type")
        in_water = False
        if gtype == "Polygon":
            ring = (geom.get("coordinates") or [[]])[0]
            frac = flood_fraction_for_polygon(ring, mask, bounds)
            in_water = frac >= area_threshold
        elif gtype in {"LineString", "MultiLineString"}:
            in_water = _line_in_water(geom, mask, bounds)
        else:
            in_water = _amenity_in_water(geom, mask, bounds)
        props["in_water"] = in_water
        props["damage_class"] = DamageClass.UNKNOWN.value if in_water else DamageClass.NONE.value
        props["note"] = QualityFlag.INUNDATION_PROXY_NOT_STRUCTURAL.value if in_water else ""
        out.append({"type": "Feature", "geometry": geom, "properties": props})
    return out
