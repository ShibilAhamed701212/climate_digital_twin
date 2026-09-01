from __future__ import annotations

import math
from typing import Any


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def line_length_km(geom: dict[str, Any]) -> float | None:
    gtype = geom.get("type")
    if gtype == "LineString":
        coords = geom.get("coordinates") or []
        return _path_km(coords)
    if gtype == "MultiLineString":
        parts = geom.get("coordinates") or []
        lengths = [_path_km(part) for part in parts]
        known = [x for x in lengths if x is not None]
        if not known:
            return None
        return sum(known)
    return None


def polygon_area_km2(ring: list[Any]) -> float | None:
    """Spherical trapezoid area (km^2) for a lon/lat ring. None if degenerate."""
    if not isinstance(ring, list) or len(ring) < 4:
        return None
    pts: list[tuple[float, float]] = []
    for p in ring:
        if not isinstance(p, list) or len(p) < 2:
            return None
        pts.append((float(p[0]), float(p[1])))
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    area = 0.0
    for i in range(len(pts) - 1):
        lon1, lat1 = math.radians(pts[i][0]), math.radians(pts[i][1])
        lon2, lat2 = math.radians(pts[i + 1][0]), math.radians(pts[i + 1][1])
        area += (lon2 - lon1) * (2.0 + math.sin(lat1) + math.sin(lat2))
    km2 = abs(area) * (6371.0**2) / 2.0
    return km2 if km2 > 0.0 else None


def geometry_envelope(geom: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Return (min_lon, min_lat, max_lon, max_lat) or None."""
    coords: list[Any] = []
    gtype = geom.get("type")
    raw = geom.get("coordinates")
    if gtype == "Point" and isinstance(raw, list) and len(raw) >= 2:
        lon, lat = float(raw[0]), float(raw[1])
        return lon, lat, lon, lat
    if gtype == "LineString" and isinstance(raw, list):
        coords = raw
    elif gtype == "Polygon" and isinstance(raw, list) and raw:
        coords = raw[0] if isinstance(raw[0], list) else []
    elif gtype == "MultiLineString" and isinstance(raw, list):
        coords = [pt for part in raw if isinstance(part, list) for pt in part]
    elif gtype == "MultiPolygon" and isinstance(raw, list):
        coords = [
            pt
            for poly in raw
            if isinstance(poly, list) and poly
            for pt in (poly[0] if isinstance(poly[0], list) else [])
        ]
    lons: list[float] = []
    lats: list[float] = []
    for p in coords:
        if isinstance(p, list) and len(p) >= 2:
            lons.append(float(p[0]))
            lats.append(float(p[1]))
    if not lons:
        return None
    return min(lons), min(lats), max(lons), max(lats)


def envelope_intersects_bbox(
    envelope: tuple[float, float, float, float],
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
) -> bool:
    gx0, gy0, gx1, gy1 = envelope
    return not (gx1 < minx or gx0 > maxx or gy1 < miny or gy0 > maxy)


def valid_lonlat(lon: float, lat: float) -> bool:
    return -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0


def close_ring(ring: list[Any]) -> list[list[float]]:
    pts: list[list[float]] = []
    for p in ring:
        if isinstance(p, list) and len(p) >= 2:
            pts.append([float(p[0]), float(p[1])])
    if len(pts) < 3:
        return pts
    if pts[0] != pts[-1]:
        pts.append(list(pts[0]))
    return pts


def simplify_ring(ring: list[Any], tolerance: float) -> list[list[float]]:
    """Drop vertices closer than `tolerance` degrees to the previous kept vertex."""
    closed = close_ring(ring)
    if tolerance <= 0 or len(closed) < 5:
        return closed
    kept = [closed[0]]
    for pt in closed[1:-1]:
        prev = kept[-1]
        if abs(pt[0] - prev[0]) >= tolerance or abs(pt[1] - prev[1]) >= tolerance:
            kept.append(pt)
    kept.append(closed[-1])
    if len(kept) < 4:
        return closed
    return kept


def simplify_geometry(geom: dict[str, Any], tolerance: float) -> dict[str, Any]:
    if tolerance <= 0:
        return geom
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if gtype == "Polygon" and isinstance(coords, list) and coords:
        return {"type": "Polygon", "coordinates": [simplify_ring(coords[0], tolerance)]}
    if gtype == "LineString" and isinstance(coords, list):
        ring = simplify_ring(list(coords) + [coords[0]] if coords else [], tolerance)
        return {"type": "LineString", "coordinates": ring[:-1] if len(ring) > 1 else ring}
    return geom


def _path_km(coords: list[Any]) -> float | None:
    if not isinstance(coords, list) or len(coords) < 2:
        return None
    total = 0.0
    for i in range(1, len(coords)):
        a, b = coords[i - 1], coords[i]
        if not isinstance(a, list) or not isinstance(b, list) or len(a) < 2 or len(b) < 2:
            return None
        total += haversine_km(float(a[0]), float(a[1]), float(b[0]), float(b[1]))
    return total
