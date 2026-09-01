from __future__ import annotations

from typing import Any

from disaster_intelligence.domain.geometry import polygon_area_km2


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        intersects = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def geometry_centroid(geom: dict[str, Any]) -> tuple[float, float] | None:
    coords = []
    gtype = geom.get("type")
    if gtype == "Point":
        c = geom.get("coordinates") or [None, None]
        return float(c[0]), float(c[1])
    if gtype == "Polygon":
        coords = (geom.get("coordinates") or [[]])[0]
    elif gtype == "LineString":
        coords = geom.get("coordinates") or []
    elif gtype == "MultiPolygon":
        coords = ((geom.get("coordinates") or [[[]]])[0] or [[]])[0]
    if not coords:
        return None
    lons = [float(p[0]) for p in coords]
    lats = [float(p[1]) for p in coords]
    return sum(lons) / len(lons), sum(lats) / len(lats)


def pixel_water(
    lon: float,
    lat: float,
    mask: list[list[int]],
    bounds: dict[str, float],
) -> bool:
    height = len(mask)
    width = len(mask[0]) if height else 0
    if width == 0:
        return False
    west, east = bounds["west"], bounds["east"]
    south, north = bounds["south"], bounds["north"]
    if east == west or north == south:
        return False
    col = int((lon - west) / (east - west) * width)
    row = int((north - lat) / (north - south) * height)
    if col < 0 or col >= width or row < 0 or row >= height:
        return False
    return mask[row][col] > 0


def flood_fraction_for_polygon(
    ring: list[list[float]],
    mask: list[list[int]],
    bounds: dict[str, float],
    samples: int = 8,
) -> float:
    if not ring:
        return 0.0
    lons = [float(p[0]) for p in ring]
    lats = [float(p[1]) for p in ring]
    hits = 0
    total = 0
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    if samples < 2:
        samples = 2
    for i in range(samples):
        for j in range(samples):
            lon = min_lon + (max_lon - min_lon) * (i + 0.5) / samples
            lat = min_lat + (max_lat - min_lat) * (j + 0.5) / samples
            if not point_in_ring(lon, lat, ring):
                continue
            total += 1
            if pixel_water(lon, lat, mask, bounds):
                hits += 1
    if total == 0:
        centroid_lon = sum(lons) / len(lons)
        centroid_lat = sum(lats) / len(lats)
        return 1.0 if pixel_water(centroid_lon, centroid_lat, mask, bounds) else 0.0
    return hits / total


def location_id_containing(
    lon: float,
    lat: float,
    location_features: list[dict[str, Any]],
) -> str | None:
    for feat in location_features:
        geom = feat.get("geometry") or {}
        loc = str((feat.get("properties") or {}).get("location_id") or "")
        if not loc:
            continue
        for ring in _rings_from_geom(geom):
            if point_in_ring(lon, lat, ring):
                return loc
    return None


def _rings_from_geom(geom: dict[str, Any]) -> list[list[list[float]]]:
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    if gtype == "Polygon" and coords:
        ring = coords[0]
        return [ring] if isinstance(ring, list) else []
    if gtype == "MultiPolygon":
        rings: list[list[list[float]]] = []
        for poly in coords:
            if isinstance(poly, list) and poly and isinstance(poly[0], list):
                rings.append(poly[0])
        return rings
    return []


def zonal_stats(
    location_features: list[dict[str, Any]],
    mask: list[list[int]],
    bounds: dict[str, float],
    pixel_area_km2: float,  # noqa: ARG001
) -> list[dict[str, Any]]:
    _ = pixel_area_km2  # retained for API compatibility; area uses polygon geometry
    rows: list[dict[str, Any]] = []
    for feat in location_features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        rings = _rings_from_geom(geom)
        areas = [polygon_area_km2(ring) or 0.0 for ring in rings]
        fracs = [flood_fraction_for_polygon(ring, mask, bounds) for ring in rings]
        loc_area = sum(areas)
        if loc_area > 0 and rings:
            frac = sum(a * f for a, f in zip(areas, fracs, strict=False)) / loc_area
        elif fracs:
            frac = sum(fracs) / len(fracs)
        else:
            frac = 0.0
        location_id = str(props.get("location_id") or "")
        pop = props.get("population")
        exposed = None
        if pop is not None and frac > 0:
            exposed = int(round(float(pop) * frac))
        rows.append(
            {
                "location_id": location_id,
                "district": props.get("district"),
                "flood_fraction": round(frac, 4),
                "flood_area_km2": round(loc_area * frac, 4) if loc_area else 0.0,
                "population": pop,
                "pop_exposed_est": exposed,
            }
        )
    return rows
