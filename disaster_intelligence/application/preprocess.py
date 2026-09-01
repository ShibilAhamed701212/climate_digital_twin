from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from disaster_intelligence.domain.errors import ValidationError
from disaster_intelligence.domain.geotiff import read_uint8_tiff, write_uint8_tiff


def quality_control(rows: list[list[int]], max_pixels: int) -> list[str]:
    height = len(rows)
    width = len(rows[0]) if rows else 0
    if height == 0 or width == 0:
        raise ValidationError("Raster is empty", "INVALID_GEOTIFF")
    if height * width > max_pixels:
        raise ValidationError("Raster exceeds max_pixels", "PAYLOAD_TOO_LARGE")
    flags: list[str] = []
    if min(width, height) < 8:
        flags.append("low_res")
    return flags


def clip_to_aoi(rows: list[list[int]]) -> list[list[int]]:
    """Upload rasters are already treated as covering the event AOI; no geotransform to crop."""
    return [list(row) for row in rows]


def speckle_median(rows: list[list[int]], radius: int = 1) -> list[list[int]]:
    """3x3 (radius=1) median filter for uint8 SAR DN. Identity when the raster is too small."""
    height = len(rows)
    width = len(rows[0]) if rows else 0
    if height < 3 or width < 3 or radius < 1:
        return clip_to_aoi(rows)
    out: list[list[int]] = []
    for y in range(height):
        row_out: list[int] = []
        for x in range(width):
            window: list[int] = []
            for dy in range(-radius, radius + 1):
                yy = min(height - 1, max(0, y + dy))
                for dx in range(-radius, radius + 1):
                    xx = min(width - 1, max(0, x + dx))
                    window.append(rows[yy][xx])
            window.sort()
            row_out.append(window[len(window) // 2])
        out.append(row_out)
    return out


def sar_preprocess(rows: list[list[int]]) -> list[list[int]]:
    """Clip (identity AOI) then speckle-median. No GRD calibration without annotated metadata."""
    return speckle_median(clip_to_aoi(rows))


def cloud_mask_flags(provider: str, product: str = "") -> list[str]:
    blob = f"{provider} {product}".lower()
    if "sentinel-2" in blob:
        return ["optical_cloud_unmasked"]
    if "sentinel-1" in blob or "s1" in blob:
        return ["s1_only"]
    return ["cloud_status_unknown"]


def cloud_mask_sar() -> list[str]:
    """Sentinel-1 GRD has no optical cloud mask; flag rather than inventing clouds."""
    return cloud_mask_flags("sentinel-1")


def make_tiles(rows: list[list[int]], tile_size: int = 256) -> list[list[list[int]]]:
    height = len(rows)
    width = len(rows[0]) if rows else 0
    tiles: list[list[list[int]]] = []
    if tile_size <= 0:
        return [rows]
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            tile = [row[x : x + tile_size] for row in rows[y : y + tile_size]]
            tiles.append(tile)
    return tiles


def write_tiles(dest_dir: Path, rows: list[list[int]], tile_size: int = 256) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    uris: list[str] = []
    for i, tile in enumerate(make_tiles(rows, tile_size)):
        h = len(tile)
        w = len(tile[0]) if tile else 0
        path = dest_dir / f"tile_{i:04d}.tif"
        write_uint8_tiff(path, tile, width=w, height=h)
        uris.append(str(path))
    return uris


def write_geoparquet_sidecar(geojson_path: Path) -> str:
    """Gzip the GeoJSON FeatureCollection as a compact sidecar (no PostGIS / pyarrow)."""
    raw = geojson_path.read_bytes()
    out = geojson_path.with_suffix(geojson_path.suffix + ".gz")
    out.write_bytes(gzip.compress(raw, compresslevel=6))
    return str(out)


def export_feature_collection(path: Path, features: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )
    write_geoparquet_sidecar(path)
    return str(path)


def load_scene_rows(uri: str) -> list[list[int]]:
    rows, _, _ = read_uint8_tiff(Path(uri))
    return rows
