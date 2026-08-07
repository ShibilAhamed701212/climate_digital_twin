"""Phase 7 — Single-layer soil water balance (bucket model).

Daily mass balance over a root-zone store (mm of plant-available water):

    S(t+1) = S(t) + P - AET - Q - D

    P      rainfall (mm)
    AET    actual evapotranspiration (mm), PET reduced when the store is
           below the readily-available depletion threshold (FAO-56 Ch. 8)
    Q      surface runoff (mm), SCS-CN
    D      drainage below the root zone (mm), any excess over capacity

All fluxes are non-negative and the store is bounded to [0, capacity].  The
bucket is a deliberate simplification of a real soil column: no multiple
layers, no explicit percolation lag, no groundwater coupling.  This is
documented as a limitation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from climatedt.simulation.processes.evapotranspiration import hargreaves_et0
from climatedt.simulation.processes.runoff import scs_runoff


@dataclass(frozen=True)
class DailyWaterBalance:
    """Per-day water balance output (all mm unless noted)."""

    date: str
    precipitation: float
    pet: float
    aet: float
    runoff: float
    drainage: float
    storage_start: float
    storage_end: float
    dryness: float  # 0 = saturated, 1 = fully depleted
    soil_moisture_m3m3: float  # deprecated — use relative_soil_water instead
    relative_soil_water: float  # storage/capacity fraction (dimensionless proxy)


def _aet(pet: float, storage: float, capacity: float, depletion_fraction: float) -> float:
    """Soil-limited actual ET (FAO-56 Ch. 8 stress reduction)."""
    if pet <= 0:
        return 0.0
    # Readily available water threshold: when the store drops below
    # (1 - depletion_fraction) * capacity, AET is linearly reduced.
    threshold = capacity * (1.0 - depletion_fraction)
    if threshold <= 0:
        return min(pet, storage)
    if storage >= threshold:
        return pet
    return pet * (storage / threshold)


def daily_water_balance(
    date: str,
    precipitation_mm: float,
    tmax_c: float,
    tmin_c: float,
    latitude_deg: float,
    jday: int,
    storage_mm: float,
    capacity_mm: float,
    antecedent_5d_mm: float,
    cn_ii: float,
    krs: float = 0.0023,
    depletion_fraction: float = 0.5,
    humidity_pct: float | None = None,
    wind_speed_ms: float | None = None,
    solar_radiation_mj: float | None = None,
    pressure_kpa: float | None = None,
) -> tuple[DailyWaterBalance, float]:
    """Advance the bucket one day.  Returns (balance, new_storage_mm).

    Uses FAO-56 Penman-Monteith when humidity, wind, and radiation are
    available; falls back to Hargreaves-Samani otherwise.

    Raises ValueError for non-physical inputs.
    """
    if not math.isfinite(precipitation_mm) or precipitation_mm < 0:
        raise ValueError(
            f"precipitation_mm must be a non-negative finite number, got {precipitation_mm!r}"
        )
    if not 0.0 <= storage_mm <= capacity_mm:
        raise ValueError(f"storage_mm must be within [0, capacity], got {storage_mm!r}")
    if not capacity_mm > 0.0:
        raise ValueError(f"capacity_mm must be positive, got {capacity_mm!r}")
    if not 0.0 <= depletion_fraction <= 1.0:
        raise ValueError(f"depletion_fraction must be in 0..1, got {depletion_fraction!r}")

    # Auto-select ET method
    all_available = all(v is not None for v in [humidity_pct, wind_speed_ms, solar_radiation_mj])
    if all_available:
        from climatedt.simulation.processes.penman_monteith import penman_monteith_et0

        pet = penman_monteith_et0(
            tmax_c,
            tmin_c,
            latitude_deg,
            jday,
            wind_speed_2m_ms=wind_speed_ms,
            rh_mean_pct=humidity_pct,
            rs_mj=solar_radiation_mj,
            pressure_kpa=pressure_kpa or 101.3,
        )
    else:
        pet = hargreaves_et0(tmax_c, tmin_c, latitude_deg, jday, krs)

    runoff = scs_runoff(precipitation_mm, cn_ii, antecedent_5d_mm)

    aet = _aet(pet, storage_mm, capacity_mm, depletion_fraction)
    aet = min(aet, storage_mm + precipitation_mm - runoff)  # never exceed available water
    aet = max(0.0, aet)

    mid = storage_mm + precipitation_mm - aet - runoff
    drainage = max(0.0, mid - capacity_mm)
    storage_end = max(0.0, min(capacity_mm, mid))

    dryness = 1.0 - (storage_end / capacity_mm if capacity_mm > 0 else 1.0)
    relative_water = storage_end / capacity_mm

    balance = DailyWaterBalance(
        date=date,
        precipitation=precipitation_mm,
        pet=pet,
        aet=aet,
        runoff=runoff,
        drainage=drainage,
        storage_start=storage_mm,
        storage_end=storage_end,
        dryness=dryness,
        soil_moisture_m3m3=relative_water,
        relative_soil_water=relative_water,
    )
    return balance, storage_end
