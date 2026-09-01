"""Sentinel-1 VV/VH load, nodata handling, and Sen1Floods11 z-score.

Channel order is always VV=0, VH=1. Polarization is taken from STAC/filename
tokens (`-vv-` / `-vh-`), never from band index guesses.

Normalization constants are the recovered S1Hand dB mean/std published with
Governor6191/sar-flood-extent (MIT), used by that U-Net checkpoint:
https://github.com/Governor6191/sar-flood-extent/blob/main/src/sen1floods11_norm_constants.json
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from disaster_intelligence.domain.errors import TaskNotEnabledError, ValidationError
from disaster_intelligence.domain.geotiff import (
    read_float32_vv_vh,
    read_uint8_tiff,
    sniff_tiff_magic,
)
from disaster_intelligence.domain.s1_assets import polarization_from_filename

# Official recovered Sen1Floods11 S1Hand dB stats (not ImageNet).
VV_MEAN = -10.85569763176121
VV_STD = 4.762064933575756
VH_MEAN = -18.10330009462964
VH_STD = 6.0552577971302295
CHANNEL_ORDER = ("VV", "VH")


@dataclass
class S1Stack:
    vv: list[list[float]]
    vh: list[list[float]]
    bounds: dict[str, float]
    crs: str = "EPSG:4326"
    polarizations: tuple[str, str] = CHANNEL_ORDER
    source: str = ""

    @property
    def height(self) -> int:
        return len(self.vv)

    @property
    def width(self) -> int:
        return len(self.vv[0]) if self.vv else 0


def sanitize_db(values: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for row in values:
        clean: list[float] = []
        for raw in row:
            v = float(raw)
            if v != v or v == float("inf") or v == float("-inf"):
                clean.append(0.0)
            else:
                clean.append(max(-50.0, min(10.0, v)))
        out.append(clean)
    return out


def standardize_vv_vh(
    vv: list[list[float]], vh: list[list[float]]
) -> tuple[list[list[float]], list[list[float]]]:
    vv_s = sanitize_db(vv)
    vh_s = sanitize_db(vh)
    vv_z = [[(v - VV_MEAN) / VV_STD for v in row] for row in vv_s]
    vh_z = [[(v - VH_MEAN) / VH_STD for v in row] for row in vh_s]
    return vv_z, vh_z


def tile_stack(
    vv: list[list[float]], vh: list[list[float]], tile: int = 512
) -> list[tuple[int, int, int, int, list[list[float]], list[list[float]]]]:
    height = len(vv)
    width = len(vv[0]) if vv else 0
    tiles = []
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            ph = min(tile, height - y)
            pw = min(tile, width - x)
            tvv = [row[x : x + pw] for row in vv[y : y + ph]]
            tvh = [row[x : x + pw] for row in vh[y : y + ph]]
            tiles.append((y, x, ph, pw, tvv, tvh))
    return tiles


def stitch_mask(
    height: int,
    width: int,
    parts: list[tuple[int, int, int, int, list[list[int]]]],
) -> list[list[int]]:
    out = [[0 for _ in range(width)] for _ in range(height)]
    for y, x, ph, pw, tile in parts:
        for r in range(ph):
            for c in range(pw):
                out[y + r][x + c] = tile[r][c]
    return out


def bounds_from_geo(geo: dict[str, float], width: int, height: int) -> dict[str, float]:
    west = float(geo.get("west") or 0.0)
    north = float(geo.get("north") or 0.0)
    xres = float(geo.get("xres") or 1.0)
    yres = abs(float(geo.get("yres") or 1.0))
    return {
        "west": west,
        "east": west + xres * width,
        "north": north,
        "south": north - yres * height,
    }


def write_s1_sidecar(path: Path, stack_tif: Path, bounds: dict[str, float]) -> str:
    payload = {
        "kind": "sentinel1-vv-vh",
        "stack": str(stack_tif),
        "channel_order": list(CHANNEL_ORDER),
        "polarizations": list(CHANNEL_ORDER),
        "crs": "EPSG:4326",
        "bounds": bounds,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _from_sidecar(path: Path) -> S1Stack:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("kind") != "sentinel1-vv-vh":
        raise ValidationError("Not a Sentinel-1 VV/VH sidecar", "INVALID_GEOTIFF")
    order = payload.get("channel_order") or CHANNEL_ORDER
    if list(order) != list(CHANNEL_ORDER):
        raise ValidationError("Unsupported channel_order; expected VV,VH", "WRONG_INPUT_CHANNELS")
    stack_path = Path(str(payload.get("stack") or ""))
    vv_path = payload.get("vv")
    vh_path = payload.get("vh")
    if stack_path.is_file():
        vv, vh, geo = read_float32_vv_vh(stack_path)
        bounds = payload.get("bounds") or bounds_from_geo(geo, len(vv[0]), len(vv))
        return S1Stack(vv=vv, vh=vh, bounds=bounds, source=str(stack_path))
    if vv_path and vh_path:
        vv, _vh_unused, geo = read_float32_vv_vh(Path(str(vv_path)))
        _ = _vh_unused
        raise ValidationError("Split vv/vh sidecar must use a 2-channel stack file", "INVALID_GEOTIFF")
    raise ValidationError("S1 sidecar is missing the stack GeoTIFF", "INVALID_GEOTIFF")


def extract_s1_measurements(archive: Path, dest: Path) -> tuple[Path, Path]:
    dest.mkdir(parents=True, exist_ok=True)
    dest_res = dest.resolve()
    vv_path: Path | None = None
    vh_path: Path | None = None
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            pol = polarization_from_filename(info.filename)
            if pol is None:
                continue
            suffix = Path(info.filename).suffix.lower()
            if suffix not in {".tif", ".tiff"}:
                continue
            target = (dest_res / f"{pol.lower()}{suffix}").resolve()
            if not str(target).startswith(str(dest_res)):
                raise ValidationError("Zip extract escaped destination")
            with zf.open(info) as src, target.open("wb") as out:
                out.write(src.read())
            if pol == "VV":
                vv_path = target
            else:
                vh_path = target
    if vv_path is None or vh_path is None:
        raise ValidationError(
            "SAFE/COG zip does not contain both VV and VH measurement GeoTIFFs",
            "INSUFFICIENT_POLARIZATION",
        )
    return vv_path, vh_path


def _rasterio_read_band(path: Path, wanted: str) -> tuple[list[list[float]], dict[str, float]]:
    try:
        import rasterio
    except Exception as exc:
        raise TaskNotEnabledError(
            f"Compressed Sentinel-1 GeoTIFF requires rasterio to read {wanted}: {exc}"
        ) from exc
    with rasterio.open(path) as src:
        tags = {str(k).upper(): str(v).upper() for k, v in (src.tags() or {}).items()}
        desc = [str(d).upper() if d else "" for d in (src.descriptions or ())]
        idx = 1
        if src.count >= 2:
            for i, name in enumerate(desc, start=1):
                if wanted in name or tags.get(f"BAND_{i}") == wanted:
                    idx = i
                    break
            else:
                idx = 1 if wanted == "VV" else min(2, src.count)
                if wanted == "VH" and src.count < 2:
                    raise ValidationError(
                        "Raster has no VH band", "INSUFFICIENT_POLARIZATION"
                    )
        elif wanted == "VH":
            raise ValidationError("Single-band raster has no VH", "INSUFFICIENT_POLARIZATION")
        arr = src.read(idx)
        transform = src.transform
        bounds = {
            "west": float(src.bounds.left),
            "east": float(src.bounds.right),
            "south": float(src.bounds.bottom),
            "north": float(src.bounds.top),
        }
        _ = transform
        rows = [[float(v) for v in row] for row in arr.tolist()]
        return rows, bounds


def load_s1_stack(uri: str) -> S1Stack | None:
    path = Path(uri)
    if not path.exists():
        return None
    if path.suffix.lower() == ".json":
        return _from_sidecar(path)
    if path.suffix.lower() == ".zip":
        vv_p, vh_p = extract_s1_measurements(path, path.with_suffix("") / "meas")
        try:
            vv, _ignore_vh, geo = read_float32_vv_vh(vv_p)
            _ignore_vv, vh, _geo2 = read_float32_vv_vh(vh_p)
            _ = _ignore_vh, _ignore_vv, _geo2
            bounds = bounds_from_geo(geo, len(vv[0]), len(vv))
            return S1Stack(vv=vv, vh=vh, bounds=bounds, source=str(path))
        except ValidationError:
            vv, b1 = _rasterio_read_band(vv_p, "VV")
            vh, b2 = _rasterio_read_band(vh_p, "VH")
            return S1Stack(vv=vv, vh=vh, bounds=b1 or b2, source=str(path))
    head = path.read_bytes()[:4]
    if not sniff_tiff_magic(head if len(head) == 4 else path.read_bytes()[:8]):
        return None
    try:
        vv, vh, geo = read_float32_vv_vh(path)
        bounds = bounds_from_geo(geo, len(vv[0]), len(vv))
        return S1Stack(vv=vv, vh=vh, bounds=bounds, source=str(path))
    except ValidationError as first:
        try:
            read_uint8_tiff(path)
            return None
        except ValidationError:
            _ = first
        try:
            vv, b1 = _rasterio_read_band(path, "VV")
            vh, b2 = _rasterio_read_band(path, "VH")
            return S1Stack(vv=vv, vh=vh, bounds=b1 or b2, source=str(path))
        except (TaskNotEnabledError, ValidationError):
            return None


def threshold_mask_from_vv(vv: list[list[float]], vv_db: float) -> list[list[int]]:
    """Open-water proxy: pixels at or below the configured VV dB threshold."""
    return [[1 if float(v) <= vv_db else 0 for v in row] for row in vv]


def clip_stack_to_max_pixels(stack: S1Stack, max_pixels: int) -> S1Stack:
    total = stack.width * stack.height
    if total <= max_pixels:
        return stack
    raise ValidationError("Raster exceeds max_pixels", "PAYLOAD_TOO_LARGE")


def window_vv_vh_to_aoi(
    vv_path: str | Path,
    vh_path: str | Path,
    aoi_bounds: dict[str, float],
    *,
    max_side: int = 3500,
    bearer_token: str | None = None,
) -> S1Stack:
    """Windowed VV/VH read (local or /vsicurl). Does not fabricate a missing polarization.

    Sentinel-1 GRD GeoTIFFs often store geolocation as GCPs (EPSG:4326) with no
    affine CRS. Those are warped to EPSG:4326 with rasterio WarpedVRT before the
    AOI window is read.
    """
    try:
        from contextlib import ExitStack

        import rasterio
        from rasterio.enums import Resampling
        from rasterio.vrt import WarpedVRT
        from rasterio.warp import reproject, transform_bounds
        from rasterio.windows import Window, from_bounds
        from rasterio.windows import bounds as window_bounds
    except Exception as exc:
        raise TaskNotEnabledError(f"AOI windowed S1 read requires rasterio: {exc}") from exc

    env_kw: dict[str, str] = {}
    if bearer_token:
        env_kw["GDAL_HTTP_HEADER"] = f"Authorization: Bearer {bearer_token}"
        env_kw["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"

    west, south = float(aoi_bounds["west"]), float(aoi_bounds["south"])
    east, north = float(aoi_bounds["east"]), float(aoi_bounds["north"])

    def _georef(stack: ExitStack, src: Any) -> Any:
        crs = getattr(src, "crs", None)
        if crs is not None:
            return src
        gcps, gcp_crs = src.gcps  # type: ignore[attr-defined]
        if gcps and gcp_crs is not None:
            return stack.enter_context(
                WarpedVRT(src, crs="EPSG:4326", resampling=Resampling.bilinear)
            )
        raise ValidationError("VV/VH raster has no CRS or GCPs", "INVALID_GEOTIFF")

    with ExitStack() as stack:
        stack.enter_context(rasterio.Env(**env_kw))
        src_vv_raw = stack.enter_context(rasterio.open(str(vv_path)))
        src_vh_raw = stack.enter_context(rasterio.open(str(vh_path)))
        if src_vv_raw.count < 1 or src_vh_raw.count < 1:
            raise ValidationError("Empty VV or VH raster", "INSUFFICIENT_POLARIZATION")
        src_vv = _georef(stack, src_vv_raw)
        src_vh = _georef(stack, src_vh_raw)
        crs_vv = src_vv.crs
        if crs_vv is None:
            raise ValidationError("VV raster has no CRS", "INVALID_GEOTIFF")
        try:
            aoi_in_vv = transform_bounds("EPSG:4326", crs_vv, west, south, east, north)
        except Exception:
            aoi_in_vv = (west, south, east, north)
        win = from_bounds(*aoi_in_vv, transform=src_vv.transform)
        win = win.intersection(Window(0, 0, src_vv.width, src_vv.height))
        if win.width < 8 or win.height < 8:
            raise ValidationError("AOI window does not overlap the VV raster", "INVALID_GEOTIFF")
        col_off = int(win.col_off)
        row_off = int(win.row_off)
        width = min(int(win.width), max_side)
        height = min(int(win.height), max_side)
        read_win = Window(col_off, row_off, width, height)
        vv_arr = src_vv.read(1, window=read_win, boundless=False).astype("float32")
        try:
            same_affine = bool(src_vh.transform.almost_equals(src_vv.transform, precision=1e-6))
        except Exception:
            same_affine = tuple(float(x) for x in src_vh.transform[:6]) == tuple(
                float(x) for x in src_vv.transform[:6]
            )
        same_grid = (
            src_vh.crs == crs_vv
            and same_affine
            and src_vh.width == src_vv.width
            and src_vh.height == src_vv.height
        )
        if same_grid:
            vh_arr = src_vh.read(1, window=read_win, boundless=False).astype("float32")
        else:
            import numpy as np

            vh_arr = np.zeros((height, width), dtype="float32")
            dst_transform = src_vv.window_transform(read_win)
            reproject(
                source=rasterio.band(src_vh, 1),
                destination=vh_arr,
                src_transform=src_vh.transform,
                src_crs=src_vh.crs,
                dst_transform=dst_transform,
                dst_crs=crs_vv,
                resampling=Resampling.bilinear,
            )
        left, bottom, right, top = window_bounds(read_win, src_vv.transform)
        try:
            wgs = transform_bounds(crs_vv, "EPSG:4326", left, bottom, right, top)
            bounds = {
                "west": float(wgs[0]),
                "south": float(wgs[1]),
                "east": float(wgs[2]),
                "north": float(wgs[3]),
            }
        except Exception:
            bounds = {
                "west": float(left),
                "south": float(bottom),
                "east": float(right),
                "north": float(top),
            }
        return S1Stack(
            vv=vv_arr.tolist(),
            vh=vh_arr.tolist(),
            bounds=bounds,
            crs="EPSG:4326",
            source=f"{vv_path}|{vh_path}",
        )
