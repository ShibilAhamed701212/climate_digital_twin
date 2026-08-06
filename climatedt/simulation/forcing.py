"""Phase 7 — Real forcing loaders for the coupled simulation.

Loads REAL observed daily forcing (Tmax, Tmin, Rainfall) from the
authoritative project data files:
  - Bengaluru point record: data/real/{training,validation,testing}.csv
  - NASA POWER grid: data/raw/{maxtemp,mintemp,rainfall}.parquet

Never synthesizes or fakes forcing: missing coverage raises a clear error.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import pandas as pd

from climatedt.simulation.models import DailyForcing, ForcingSource

logger = logging.getLogger(__name__)

REAL_DIR = Path("data/real")
RAW_DIR = Path("data/raw")

BENGALURU_LOCATION = "bengaluru"
GRID_LOCATION_PREFIX = "grid"


def load_bengaluru_forcing() -> tuple[list[DailyForcing], ForcingSource]:
    """Load the full validated Bengaluru point record (2021-2026)."""
    frames = []
    for split in ("training", "validation", "testing"):
        path = REAL_DIR / f"{split}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Bengaluru real data file missing: {path}")
        df = pd.read_csv(path)
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    combined["Date"] = pd.to_datetime(combined["Date"])
    combined = combined.sort_values("Date").drop_duplicates(subset="Date")
    combined = combined[["Date", "MaxTemp", "MinTemp", "Rainfall"]].dropna()
    combined = combined.rename(
        columns={"MaxTemp": "tmax", "MinTemp": "tmin", "Rainfall": "rainfall"}
    )

    rows = _to_forcing(combined)
    source = ForcingSource(
        name="open-meteo-bengaluru",
        path="data/real/{training,validation,testing}.csv",
        rows=len(combined),
        start_date=str(combined["Date"].min().date()),
        end_date=str(combined["Date"].max().date()),
        variables=("tmax", "tmin", "rainfall"),
        authenticity="REAL",
    )
    return rows, source


def load_grid_forcing(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> tuple[list[DailyForcing], ForcingSource]:
    """Load NASA POWER grid-cell daily forcing for a bounding window.

    Loads the full grid cell then slices to [start, end] so antecedent
    rainfall used for runoff AMC includes days before ``start_date`` only
    when they fall inside the window — for event replay the caller should
    request a window with warm-up days before the event.
    """
    tmax_path = RAW_DIR / "maxtemp.parquet"
    tmin_path = RAW_DIR / "mintemp.parquet"
    rain_path = RAW_DIR / "rainfall.parquet"
    for p in (tmax_path, tmin_path, rain_path):
        if not p.exists():
            raise FileNotFoundError(f"Grid data file missing: {p}")

    tmax = pd.read_parquet(tmax_path)
    tmin = pd.read_parquet(tmin_path)
    rain = pd.read_parquet(rain_path)

    tmax = tmax[(tmax["Latitude"] == latitude) & (tmax["Longitude"] == longitude)]
    tmin = tmin[(tmin["Latitude"] == latitude) & (tmin["Longitude"] == longitude)]
    rain = rain[(rain["Latitude"] == latitude) & (rain["Longitude"] == longitude)]

    if tmax.empty or tmin.empty or rain.empty:
        raise ValueError(f"No grid data at lat={latitude}, lon={longitude}")

    merged = tmax.merge(tmin, on="Date", how="inner").merge(rain, on="Date", how="inner")
    merged["Date"] = pd.to_datetime(merged["Date"])
    merged = merged.sort_values("Date").drop_duplicates(subset="Date")
    merged = merged[
        (merged["Date"] >= pd.Timestamp(start_date)) & (merged["Date"] <= pd.Timestamp(end_date))
    ]
    if merged.empty:
        raise ValueError(
            f"No grid data in window {start_date}..{end_date} at {latitude},{longitude}"
        )

    df = merged.rename(columns={"MaxTemp": "tmax", "MinTemp": "tmin", "Rainfall": "rainfall"})
    rows = _to_forcing(df)
    source = ForcingSource(
        name="nasa-power-grid",
        path="data/raw/{maxtemp,mintemp,rainfall}.parquet",
        rows=len(df),
        start_date=str(df["Date"].min().date()),
        end_date=str(df["Date"].max().date()),
        variables=("tmax", "tmin", "rainfall"),
        authenticity="REAL",
    )
    return rows, source


def _to_forcing(df: pd.DataFrame) -> list[DailyForcing]:
    rows: list[DailyForcing] = []
    for _, r in df.iterrows():
        date = r["Date"]
        if isinstance(date, str):
            date = pd.Timestamp(date)
        rows.append(
            DailyForcing(
                date=date.strftime("%Y-%m-%d"),
                tmax_c=float(r["tmax"]),
                tmin_c=float(r["tmin"]),
                rainfall_mm=float(r["rainfall"]),
            )
        )
    return rows


def daily_antecedent_rainfall(days: list[DailyForcing]) -> list[float]:
    """5-day antecedent rainfall (mm) preceding each day."""
    out: list[float] = []
    window: list[float] = []
    for day in days:
        out.append(sum(window) if window else 0.0)
        window.append(day.rainfall_mm)
        if len(window) > 5:
            window.pop(0)
    return out


def monthly_d_from_daily(
    days: list[DailyForcing],
    latitude_deg: float = 12.97,
) -> dict[str, float]:
    """Monthly P - PET (mm) for SPEI, keyed by 'YYYY-MM'.

    Latitude defaults to Bengaluru (12.97 N) for backward compatibility
    when called from single-location code, but every caller should pass
    the correct location latitude explicitly.
    """
    from climatedt.simulation.processes.evapotranspiration import hargreaves_et0

    monthly: dict[str, list[float]] = {}
    for day in days:
        jday = dt.date.fromisoformat(day.date).timetuple().tm_yday
        pet = hargreaves_et0(day.tmax_c, day.tmin_c, latitude_deg, jday)
        key = day.date[:7]
        monthly.setdefault(key, [0.0, 0.0])
        monthly[key][0] += day.rainfall_mm
        monthly[key][1] += pet
    return {k: p - pet for k, (p, pet) in monthly.items()}
