"""Phase 7 — CoupledSimulationEngine.

Deterministic daily temporal loop over the coupled land-surface processes:

    PET (Hargreaves-Samani) ──► soil-limited AET
    P  + antecedent 5-day ──► SCS-CN runoff
    S(t+1) = S(t) + P - AET - Runoff - Drainage   (bounded bucket)

Pure function of (forcing, parameters, initial condition): no randomness,
no hidden state, no hardcoded outputs.  The first ``spinup_days`` are
physical warm-up and are excluded from reported results.
"""

from __future__ import annotations

import datetime as dt

from climatedt.simulation.models import (
    SPINUP_DAYS,
    DailyForcing,
    ForcingSource,
    SimulationRun,
    SimulationStep,
    build_provenance,
)
from climatedt.simulation.parameters import SimulationParameters
from climatedt.simulation.processes.soil_water import daily_water_balance

# Documented equation set included in every run's provenance.
EQUATIONS: list[dict[str, str]] = [
    {
        "process": "reference evapotranspiration",
        "equation": "ET0 = krs * (Tmean + 17.8) * (Tmax - Tmin)^0.5 * Ra",
        "source": "Hargreaves & Samani (1985); FAO-56 Ch.4 Eq.52",
        "unit": "mm/day",
    },
    {
        "process": "extraterrestrial radiation",
        "equation": "Ra = (24*60/pi) * Gsc * dr * (ws*sin(phi)*sin(delta) + cos(phi)*cos(delta)*sin(ws))",
        "source": "FAO-56 Ch.3 Eq.21",
        "unit": "MJ/m2/day (x0.408 -> mm/day)",
    },
    {
        "process": "surface runoff",
        "equation": "Q = (P - 0.2S)^2 / (P + 0.8S); S = 25400/CN - 254; CN adjusted for AMC via 5-day antecedent rainfall",
        "source": "USDA SCS NRCS NEH-4 (curve number method)",
        "unit": "mm",
    },
    {
        "process": "soil water balance",
        "equation": "S(t+1) = S(t) + P - AET - Q - Drainage (0 <= S <= capacity)",
        "source": "conceptual single-layer bucket; FAO-56 Ch.8 water balance",
        "unit": "mm",
    },
    {
        "process": "soil moisture",
        "equation": "soil_moisture_m3m3 = storage_mm / capacity_mm (relative to capacity)",
        "source": "defined in this project (bucket fills 0..capacity)",
        "unit": "m3/m3",
    },
]


class CoupledSimulationEngine:
    """Deterministic coupled land-surface simulation engine."""

    def __init__(self, spinup_days: int = SPINUP_DAYS) -> None:
        self.spinup_days = spinup_days

    def run(
        self,
        forcing: list[DailyForcing],
        *,
        location_id: str,
        forcing_source: ForcingSource,
        parameters: SimulationParameters | None = None,
    ) -> SimulationRun:
        """Run the coupled simulation over the given daily forcing.

        Raises ValueError for empty forcing or missing dates.
        """
        if not forcing:
            raise ValueError("Simulation requires at least one day of forcing")
        params = _default_parameters(location_id) if parameters is None else parameters

        steps: list[SimulationStep] = []
        storage = params.initial_storage_mm
        antecedent: list[float] = []  # previous 5 days of rainfall, oldest first

        # Validate forcing is chronological and gap-free.
        prev = None
        for day in forcing:
            current = dt.date.fromisoformat(day.date)
            if prev is not None and (current - prev).days != 1:
                raise ValueError(
                    f"Forcing must be continuous daily data; gap between "
                    f"{prev.isoformat()} and {day.date}"
                )
            prev = current

        for day in forcing:
            jday = dt.date.fromisoformat(day.date).timetuple().tm_yday
            antecedent_5d = sum(antecedent) if antecedent else 0.0

            balance, storage = daily_water_balance(
                date=day.date,
                precipitation_mm=day.rainfall_mm,
                tmax_c=day.tmax_c,
                tmin_c=day.tmin_c,
                latitude_deg=params.latitude,
                jday=jday,
                storage_mm=storage,
                capacity_mm=params.capacity_mm,
                antecedent_5d_mm=antecedent_5d,
                cn_ii=params.cn_ii,
                krs=params.krs,
                depletion_fraction=params.depletion_fraction,
                humidity_pct=day.humidity_pct,
                wind_speed_ms=day.wind_speed_ms,
                solar_radiation_mj=day.solar_radiation_mj,
                pressure_kpa=day.pressure_kpa,
            )
            steps.append(
                SimulationStep(
                    date=day.date,
                    pet_mm=balance.pet,
                    aet_mm=balance.aet,
                    runoff_mm=balance.runoff,
                    drainage_mm=balance.drainage,
                    storage_start_mm=balance.storage_start,
                    storage_mm=balance.storage_end,
                    dryness=balance.dryness,
                    soil_moisture_m3m3=balance.soil_moisture_m3m3,
                    relative_soil_water=balance.relative_soil_water,
                    precipitation_mm=balance.precipitation,
                )
            )
            antecedent.append(day.rainfall_mm)
            if len(antecedent) > 5:
                antecedent.pop(0)

        reported = steps[self.spinup_days :]
        if not reported:
            raise ValueError(
                f"Spin-up ({self.spinup_days} days) longer than forcing "
                f"({len(steps)} days); no results remain"
            )

        provenance = build_provenance(
            location_id=location_id,
            forcing=forcing_source,
            parameters=params.to_dict(),
            parameter_sources=params.parameter_sources(),
            initial_condition_mm=params.initial_storage_mm,
            equations=EQUATIONS,
        )

        return SimulationRun(
            run_id="",
            location_id=location_id,
            forcing=forcing_source,
            parameters=params.to_dict(),
            parameter_sources=params.parameter_sources(),
            initial_condition_mm=params.initial_storage_mm,
            spinup_days=self.spinup_days,
            steps=reported,
            provenance=provenance,
        )


def _default_parameters(location_id: str) -> SimulationParameters:
    """Default parameter set for a known location (Bangalore default)."""
    if location_id in ("karnataka-grid", "grid-12.5-78.0"):
        return SimulationParameters(location_id=location_id, latitude=12.5, longitude=78.0)
    return SimulationParameters(location_id=location_id)
