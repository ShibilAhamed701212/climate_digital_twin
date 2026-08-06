"""Phase 14 — Grid Twin Store.

Multi-grid version of the Digital Twin. Each ERA5 grid cell is an
independent Twin with state, history, and provenance. Built on xarray
for efficient spatial operations.

651 Karnataka cells at 0.25deg resolution.
"""

from __future__ import annotations

import json
import logging
import math
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

logger = logging.getLogger(__name__)

KARNATAKA_ERA5_DIR = Path("data/validation/era5/karnataka/raw")


@xr.register_dataset_accessor("grid_twin")
class GridTwinAccessor:
    """Accessor for xarray Dataset that adds Twin semantics."""

    def __init__(self, xarray_obj: xr.Dataset) -> None:
        self._obj = xarray_obj

    def cell_state(self, lat_idx: int, lon_idx: int, time_idx: int = -1) -> dict[str, Any]:
        """Get the Twin state for a specific grid cell at a specific time."""
        ds = self._obj
        lat = float(ds.latitude.isel(latitude=lat_idx))
        lon = float(ds.longitude.isel(longitude=lon_idx))
        t = ds.valid_time.isel(valid_time=time_idx)
        t2m = float(ds.t2m.isel(latitude=lat_idx, longitude=lon_idx, valid_time=time_idx)) - 273.15
        d2m = float(ds.d2m.isel(latitude=lat_idx, longitude=lon_idx, valid_time=time_idx)) - 273.15
        sp = float(ds.sp.isel(latitude=lat_idx, longitude=lon_idx, valid_time=time_idx)) / 100.0
        u10 = float(ds.u10.isel(latitude=lat_idx, longitude=lon_idx, valid_time=time_idx))
        v10 = float(ds.v10.isel(latitude=lat_idx, longitude=lon_idx, valid_time=time_idx))
        wind_speed = np.sqrt(u10**2 + v10**2)
        rh = float(
            100.0
            * np.exp(17.625 * (d2m + 273.15) / ((d2m + 273.15) + 243.04))
            / np.exp(17.625 * (t2m + 273.15) / ((t2m + 273.15) + 243.04))
        )

        return {
            "location_id": f"grid-{lat:.2f}-{lon:.2f}",
            "latitude": lat,
            "longitude": lon,
            "timestamp": str(t.values),
            "temperature_2m": round(t2m, 2),
            "dewpoint_2m": round(d2m, 2),
            "relative_humidity_pct": round(rh, 1),
            "pressure_hpa": round(sp, 1),
            "wind_speed_ms": round(wind_speed, 2),
            "authenticity": "REAL",
            "provider": "ECMWF_ERA5",
            "dataset": "reanalysis-era5-single-levels",
            "grid_resolution": "0.25deg",
        }

    @property
    def grid_shape(self) -> tuple[int, int]:
        """Number of (lat, lon) cells."""
        return len(self._obj.latitude), len(self._obj.longitude)

    @property
    def cell_count(self) -> int:
        """Total grid cells."""
        return self.grid_shape[0] * self.grid_shape[1]

    def bbox_cells(
        self, lat_min: float, lat_max: float, lon_min: float, lon_max: float
    ) -> list[dict[str, Any]]:
        """Get all cell states within a bounding box."""
        ds = self._obj
        lat_mask = (ds.latitude >= lat_min) & (ds.latitude <= lat_max)
        lon_mask = (ds.longitude >= lon_min) & (ds.longitude <= lon_max)
        if not lat_mask.any() or not lon_mask.any():
            return []
        ds_subset = ds.isel(latitude=lat_mask, longitude=lon_mask)
        cells = []
        for li in range(len(ds_subset.latitude)):
            for lj in range(len(ds_subset.longitude)):
                cells.append(self.cell_state(li, lj))
        return cells

    def to_dataframe(self, time_idx: int = -1) -> pd.DataFrame:
        """Convert current grid state to a pandas DataFrame."""
        ds = self._obj
        t2m = ds.t2m.isel(valid_time=time_idx) - 273.15
        d2m = ds.d2m.isel(valid_time=time_idx) - 273.15
        sp_hpa = ds.sp.isel(valid_time=time_idx) / 100.0
        u10 = ds.u10.isel(valid_time=time_idx)
        v10 = ds.v10.isel(valid_time=time_idx)
        wind = np.sqrt(u10**2 + v10**2)

        return pd.DataFrame(
            {
                "latitude": np.repeat(ds.latitude.values, len(ds.longitude)),
                "longitude": np.tile(ds.longitude.values, len(ds.latitude)),
                "temperature_c": t2m.values.ravel(),
                "dewpoint_c": d2m.values.ravel(),
                "pressure_hpa": sp_hpa.values.ravel(),
                "wind_speed_ms": wind.values.ravel(),
            }
        )


def _open_zip_member(fp: Path, member_name: str) -> xr.Dataset:
    """Extract a CDS-wrapped ZIP NetCDF member and open it with xarray."""
    fd, tmp = tempfile.mkstemp(suffix=".nc")
    os.close(fd)
    try:
        with zipfile.ZipFile(fp) as z:
            with z.open(member_name) as src, open(tmp, "wb") as dst:
                dst.write(src.read())
        return xr.open_dataset(tmp)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _extraterrestrial_radiation(jday: int, latitude_deg: float) -> float:
    """FAO-56 Eq 21 — extraterrestrial radiation Ra in MJ/m2/day."""
    phi = math.radians(latitude_deg)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * jday / 365.0)
    decl = 0.409 * math.sin(2.0 * math.pi * jday / 365.0 - 1.39)
    cos_omega = max(-1.0, min(1.0, -math.tan(phi) * math.tan(decl)))
    omega_s = math.acos(cos_omega)
    ra = (
        (24.0 * 60.0 / math.pi)
        * 0.0820
        * dr
        * (
            omega_s * math.sin(phi) * math.sin(decl)
            + math.cos(phi) * math.cos(decl) * math.sin(omega_s)
        )
    )
    return max(0.0, ra)


def _et0_hargreaves_grid(t_c: np.ndarray, lats: np.ndarray, jday: int) -> np.ndarray:
    """Vectorized Hargreaves-Samani ET0 (mm/day) over a 2-D grid.

    ponytail: uses a fixed 5 degC diurnal range as the mean monthly
    approximation — the standard FAO-56 recommendation when only mean
    daily temperature is available.  Upgrade to hourly min/max when
    sub-daily accuracy is needed.
    """
    diurnal = 5.0
    ra = np.array(
        [[_extraterrestrial_radiation(jday, float(la)) for _ in range(t_c.shape[1])] for la in lats]
    )
    ra_mm = ra * 0.408
    tmax = t_c + diurnal
    tmin = t_c - diurnal
    delta = np.maximum(tmax - tmin, 0.01)
    tmean = t_c
    return 0.0023 * (tmean + 17.8) * np.sqrt(delta) * ra_mm


def load_karnataka_grid(year: int = 2021, month: int = 1) -> xr.Dataset:
    """Load Karnataka ERA5 grid from the downloaded dataset."""
    fp = KARNATAKA_ERA5_DIR / f"era5_{year}{month:02d}.nc"
    if not fp.exists():
        raise FileNotFoundError(
            f"Karnataka ERA5 file not found: {fp}. Run the ERA5 download script first."
        )

    with zipfile.ZipFile(fp) as z:
        names = z.namelist()
        instant = next((n for n in names if n.endswith(".nc") and "instant" in n), None)
        if not instant:
            raise ValueError(f"No instant NetCDF found in {fp}")
        try:
            z.extract(instant, KARNATAKA_ERA5_DIR)
        except (FileExistsError, PermissionError):
            pass
        actual_path = KARNATAKA_ERA5_DIR / instant
        ds = xr.open_dataset(actual_path)
        logger.info("Loaded Karnataka grid: %s, %d cells", fp.name, ds.grid_twin.cell_count)
        return ds


def load_india_grid(year: int = 2021, month: int = 1) -> xr.Dataset:
    """Load India ERA5 grid."""
    fp = Path("data/validation/era5/india/raw") / f"era5_{year}{month:02d}.nc"
    if not fp.exists():
        raise FileNotFoundError(f"India ERA5 file not found: {fp}")

    with zipfile.ZipFile(fp) as z:
        names = z.namelist()
        instant = next((n for n in names if n.endswith(".nc") and "instant" in n), None)
        if not instant:
            raise ValueError(f"No instant NetCDF found in {fp}")
        extract_dir = Path("data/validation/era5/india/raw")
        try:
            z.extract(instant, extract_dir)
        except (FileExistsError, PermissionError):
            pass
        actual_path = extract_dir / instant
        ds = xr.open_dataset(actual_path)
        logger.info("Loaded India grid: %s, %d cells", fp.name, ds.grid_twin.cell_count)
        return ds


def find_nearest_cell(ds: xr.Dataset, lat: float, lon: float) -> dict[str, Any]:
    """Find the grid cell nearest to a given lat/lon."""
    lat_idx = int(np.abs(ds.latitude - lat).argmin())
    lon_idx = int(np.abs(ds.longitude - lon).argmin())
    return ds.grid_twin.cell_state(lat_idx, lon_idx)


def find_bengaluru_cell() -> dict[str, Any]:
    """Get Bengaluru's grid cell state."""
    ds = load_karnataka_grid()
    return find_nearest_cell(ds, 12.97, 77.59)


def load_karnataka_time_series(
    years: tuple[int, ...] = (2021, 2022, 2023),
) -> pd.DataFrame:
    """Load all Karnataka monthly grids into a stacked time-series DataFrame.

    Returns one row per cell per available (year, month).  Uses the last
    hourly instant of each month as the representative monthly state.
    Columns: latitude, longitude, timestamp, temperature_c, humidity_pct,
    pressure_hpa, wind_speed_ms, rainfall_mm, et0_mm.
    """
    frames: list[pd.DataFrame] = []
    for year in years:
        for month in range(1, 13):
            fp = KARNATAKA_ERA5_DIR / f"era5_{year}{month:02d}.nc"
            if not fp.exists():
                continue
            try:
                with zipfile.ZipFile(fp) as z:
                    names = z.namelist()
                    instant = next((n for n in names if n.endswith(".nc") and "instant" in n), None)
                    accum = next((n for n in names if n.endswith(".nc") and "accum" in n), None)
                    if not instant:
                        continue
                    inst = _open_zip_member(fp, instant)
                    acc = _open_zip_member(fp, accum) if accum else None
            except Exception as exc:
                logger.warning("Skipping %s: %s", fp.name, exc)
                continue
            try:
                lats = inst.latitude.values
                lons = inst.longitude.values
                t2m = inst.t2m.isel(valid_time=-1).values - 273.15
                d2m = inst.d2m.isel(valid_time=-1).values - 273.15
                sp = inst.sp.isel(valid_time=-1).values / 100.0
                u10 = inst.u10.isel(valid_time=-1).values
                v10 = inst.v10.isel(valid_time=-1).values
                wind = np.sqrt(u10**2 + v10**2)
                rh = np.clip(
                    100.0
                    * np.exp(17.625 * (d2m + 273.15) / (d2m + 273.15 + 243.04))
                    / np.exp(17.625 * (t2m + 273.15) / (t2m + 273.15 + 243.04)),
                    0.0,
                    100.0,
                )
                rainfall = np.zeros_like(t2m)
                if acc is not None and "tp" in acc:
                    rainfall = acc.tp.isel(valid_time=-1).values * 1000.0
                tv = inst.valid_time.isel(valid_time=-1).values
                jd = int(pd.Timestamp(tv).dayofyear)
                et0 = _et0_hargreaves_grid(t2m, lats, jd)
                frames.append(
                    pd.DataFrame(
                        {
                            "latitude": np.repeat(lats, len(lons)),
                            "longitude": np.tile(lons, len(lats)),
                            "timestamp": tv,
                            "temperature_c": t2m.ravel(),
                            "humidity_pct": rh.ravel(),
                            "pressure_hpa": sp.ravel(),
                            "wind_speed_ms": wind.ravel(),
                            "rainfall_mm": rainfall.ravel(),
                            "et0_mm": et0.ravel(),
                        }
                    )
                )
            except Exception as exc:
                logger.warning("Failed to process %s: %s", fp.name, exc)
                continue
    if not frames:
        raise FileNotFoundError(
            f"No Karnataka grids found under {KARNATAKA_ERA5_DIR}. "
            "Run the ERA5 download script first."
        )
    return pd.concat(frames, ignore_index=True)
