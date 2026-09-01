from __future__ import annotations


def apply_nodata(rows: list[list[int]], nodata: int = 0, fill: int = 0) -> list[list[int]]:
    out: list[list[int]] = []
    for row in rows:
        out.append([fill if px == nodata else px for px in row])
    return out


def raster_stats(rows: list[list[int]], nodata: int | None = None) -> dict[str, float | int]:
    values: list[int] = []
    for row in rows:
        for px in row:
            if nodata is not None and px == nodata:
                continue
            values.append(int(px))
    if not values:
        return {"count": 0, "min": 0, "max": 0, "mean": 0.0, "sum": 0}
    total = sum(values)
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(total / len(values), 4),
        "sum": total,
    }


def water_fraction(rows: list[list[int]], water_dn: int = 1) -> float:
    if not rows or not rows[0]:
        return 0.0
    total = len(rows) * len(rows[0])
    hit = sum(1 for row in rows for px in row if px == water_dn)
    return round(hit / total, 6) if total else 0.0


def valid_epsg(code: str) -> bool:
    raw = code.strip().upper()
    if raw.startswith("EPSG:"):
        raw = raw.split(":", 1)[1]
    return raw.isdigit() and 0 < int(raw) < 100000
