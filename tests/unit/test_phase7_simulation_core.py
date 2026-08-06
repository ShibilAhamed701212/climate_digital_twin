"""Phase 7 — Coupled simulation core tests.

Reference cases (published values):
  - Hargreaves-Samani: FAO-56 Example 20 -> ET0 = 5.03 mm/day.
  - SCS-CN: published example (P=74.4, CN=76.8, AMC-II) -> Q = 25.7 mm.
  - AMC conversion: NEH-4 equations reproduce the classic factor table.
"""

from __future__ import annotations

import datetime as dt
import math

import pytest

from climatedt.simulation.engine import CoupledSimulationEngine
from climatedt.simulation.models import DailyForcing, ForcingSource
from climatedt.simulation.processes.drought import fit_loglogistic, spei_classify, spei_from_monthly
from climatedt.simulation.processes.evapotranspiration import (
    extraterrestrial_radiation,
    hargreaves_et0,
)
from climatedt.simulation.processes.runoff import _effective_cn, scs_runoff
from climatedt.simulation.processes.soil_water import daily_water_balance


# ── evapotranspiration ──────────────────────────────────────────────────


def test_extraterrestrial_radiation_fao_example_20():
    # FAO-56 Example 20: lat 45.72, jday 196 -> Ra = 40.55 MJ/m2/day.
    assert extraterrestrial_radiation(196, 45.72) == pytest.approx(40.55, abs=0.02)


def test_hargreaves_et0_fao_example_20():
    # FAO-56 Example 20: Tmax 26.6, Tmin 14.8 -> ET0 = 5.03 mm/day.
    et0 = hargreaves_et0(26.6, 14.8, 45.72, 196)
    assert et0 == pytest.approx(5.03, abs=0.01)


def test_hargreaves_rejects_non_physical_inputs():
    with pytest.raises(ValueError):
        hargreaves_et0(20.0, 25.0, 12.97, 100)  # tmin > tmax
    with pytest.raises(ValueError):
        hargreaves_et0(25.0, 25.0, 12.97, 100)  # tmax == tmin
    with pytest.raises(ValueError):
        hargreaves_et0(float("nan"), 15.0, 12.97, 100)


def test_hargreaves_zero_at_both_poles_equator_tropical_sane():
    # Equatorial day: ET0 in a plausible tropical range (2-7 mm/day).
    for jday in (1, 80, 172, 264, 356):
        et0 = hargreaves_et0(32.0, 22.0, 12.97, jday)
        assert 2.0 < et0 < 8.0


# ── SCS-CN runoff ───────────────────────────────────────────────────────


def test_scs_runoff_published_example():
    # Published example (CN=76.8 AMC-II, P=74.4, antecedent 37.1) -> Q=25.7.
    assert scs_runoff(74.4, 76.8, antecedent_5d_mm=37.1) == pytest.approx(25.7, abs=0.2)


def test_scs_runoff_no_runoff_below_initial_abstraction():
    assert scs_runoff(1.0, 70.0, antecedent_5d_mm=0.0) == 0.0


def test_scs_runoff_monotonic_in_rainfall_and_wetness():
    q_dry = scs_runoff(50.0, 70.0, antecedent_5d_mm=10.0)
    q_wet = scs_runoff(50.0, 70.0, antecedent_5d_mm=80.0)
    q_more = scs_runoff(80.0, 70.0, antecedent_5d_mm=10.0)
    assert q_dry <= q_wet
    assert q_dry <= q_more


def test_amc_conversion_matches_factor_table():
    # NEH-4 conversions: CN=70 -> AMC-I ~50.6 (x0.73), AMC-III ~84.5 (x1.21).
    assert _effective_cn(70.0, 10.0) == pytest.approx(50.6, abs=0.5)
    assert _effective_cn(70.0, 80.0) == pytest.approx(84.5, abs=0.5)
    assert _effective_cn(70.0, 45.0) == pytest.approx(70.0, abs=1e-9)  # AMC-II


def test_scs_runoff_rejects_non_physical():
    with pytest.raises(ValueError):
        scs_runoff(-1.0, 70.0)
    with pytest.raises(ValueError):
        scs_runoff(10.0, 150.0)
    with pytest.raises(ValueError):
        scs_runoff(10.0, 70.0, antecedent_5d_mm=-1.0)


# ── soil water bucket ───────────────────────────────────────────────────


def test_bucket_mass_balance_exact():
    storage = 75.0
    for _ in range(30):
        bal, storage = daily_water_balance(
            date="2022-01-01",
            precipitation_mm=5.0,
            tmax_c=30.0,
            tmin_c=20.0,
            latitude_deg=12.97,
            jday=1,
            storage_mm=storage,
            capacity_mm=150.0,
            antecedent_5d_mm=10.0,
            cn_ii=70.0,
        )
        residual = (
            bal.storage_end
            - bal.storage_start
            - bal.precipitation
            + bal.aet
            + bal.runoff
            + bal.drainage
        )
        assert residual == pytest.approx(0.0, abs=1e-9)
    assert 0.0 <= storage <= 150.0


def test_bucket_bounded_by_capacity():
    storage = 140.0
    bal, storage = daily_water_balance(
        date="2022-01-01",
        precipitation_mm=100.0,
        tmax_c=30.0,
        tmin_c=20.0,
        latitude_deg=12.97,
        jday=1,
        storage_mm=storage,
        capacity_mm=150.0,
        antecedent_5d_mm=10.0,
        cn_ii=70.0,
    )
    assert storage <= 150.0
    assert bal.drainage == pytest.approx(
        bal.storage_start + bal.precipitation - bal.aet - bal.runoff - 150.0, abs=1e-6
    )


def test_bucket_never_negative():
    storage = 1.0
    bal, storage = daily_water_balance(
        date="2022-01-01",
        precipitation_mm=0.0,
        tmax_c=40.0,
        tmin_c=30.0,
        latitude_deg=12.97,
        jday=180,
        storage_mm=storage,
        capacity_mm=150.0,
        antecedent_5d_mm=0.0,
        cn_ii=70.0,
    )
    assert storage >= 0.0


def test_bucket_aet_soil_limited():
    # With a dry store and high PET, AET must be less than PET.
    bal, _ = daily_water_balance(
        date="2022-04-01",
        precipitation_mm=0.0,
        tmax_c=35.0,
        tmin_c=22.0,
        latitude_deg=12.97,
        jday=91,
        storage_mm=20.0,
        capacity_mm=150.0,
        antecedent_5d_mm=0.0,
        cn_ii=70.0,
    )
    assert bal.pet > 0.0
    assert bal.aet <= bal.pet
    assert bal.aet >= 0.0


def test_daily_water_balance_rejects_bad_storage():
    with pytest.raises(ValueError):
        daily_water_balance(
            date="2022-01-01",
            precipitation_mm=0.0,
            tmax_c=30.0,
            tmin_c=20.0,
            latitude_deg=12.97,
            jday=1,
            storage_mm=200.0,  # above capacity
            capacity_mm=150.0,
            antecedent_5d_mm=0.0,
            cn_ii=70.0,
        )


# ── SPEI ────────────────────────────────────────────────────────────────


def test_spei_fit_loglogistic_recovers_known_params():
    # A series whose L-skewness maps to beta ~ 2 (synthetic check).
    x = [0.1, 0.4, 0.9, 1.7, 2.8, 4.2, 5.9, 7.8, 9.9, 12.0]
    params = fit_loglogistic(x)
    assert params.beta > 1.0
    assert params.alpha > 0.0
    assert params.gamma < min(x)


def test_spei_starts_with_nan_then_standardizes():
    import random

    random.seed(42)
    sp = spei_from_monthly([random.uniform(-50, 150) for _ in range(60)], scale=3)
    assert math.isnan(sp[0]) and math.isnan(sp[1])
    assert all(not math.isnan(v) for v in sp[2:])
    vals = [v for v in sp[2:] if not math.isnan(v)]
    assert abs(sum(vals) / len(vals)) < 0.2  # standardized -> mean near zero


def test_spei_classify():
    assert spei_classify(2.1) == "EXTREME_WET"
    assert spei_classify(0.5) == "NEAR_NORMAL"
    assert spei_classify(-1.3) == "MODERATE_DROUGHT"
    assert spei_classify(-2.3) == "EXTREME_DROUGHT"
    assert spei_classify(float("nan")) == "UNKNOWN"


def test_spei_rejects_bad_scale():
    with pytest.raises(ValueError):
        spei_from_monthly([1.0, 2.0, 3.0], scale=0)


# ── engine ──────────────────────────────────────────────────────────────


def _forcing(days: int, *, monsoon: bool = True) -> list[DailyForcing]:
    start = dt.date(2022, 1, 1)
    out = []
    for i in range(days):
        d = start + dt.timedelta(days=i)
        rain = (i % 7) * 8.0 if (monsoon and d.month in (6, 7, 8, 9)) else 0.0
        out.append(DailyForcing(d.isoformat(), 30.0, 20.0, rain))
    return out


def _source(days: list[DailyForcing]) -> ForcingSource:
    return ForcingSource(
        "synthetic",
        "inline",
        len(days),
        days[0].date,
        days[-1].date,
        ("tmax", "tmin", "rainfall"),
    )


def test_engine_reports_spinup_only():
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(_forcing(400), location_id="bengaluru", forcing_source=_source(_forcing(400)))
    assert len(run.steps) == 310


def test_engine_mass_balance_and_bounds():
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(_forcing(400), location_id="bengaluru", forcing_source=_source(_forcing(400)))
    assert abs(run.mass_balance["residual_mm"]) < 1e-6
    assert all(0.0 <= s.storage_mm <= 150.0 for s in run.steps)
    assert all(0.0 <= s.soil_moisture_m3m3 <= 1.0 for s in run.steps)
    assert all(0.0 <= s.dryness <= 1.0 for s in run.steps)


def test_engine_deterministic():
    engine = CoupledSimulationEngine(spinup_days=90)
    f = _forcing(400)
    src = _source(f)
    r1 = engine.run(f, location_id="bengaluru", forcing_source=src)
    r2 = engine.run(f, location_id="bengaluru", forcing_source=src)
    assert [s.storage_mm for s in r1.steps] == [s.storage_mm for s in r2.steps]


def test_engine_authenticity_is_simulated():
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(_forcing(200), location_id="bengaluru", forcing_source=_source(_forcing(200)))
    assert run.authenticity == "SIMULATED"
    assert run.provenance["authenticity"] == "SIMULATED"
    assert run.provenance["forcing"]["authenticity"] == "REAL"


def test_engine_rejects_gaps():
    f = _forcing(10)
    f = f[:5] + f[7:]  # drop one day -> gap
    engine = CoupledSimulationEngine(spinup_days=2)
    with pytest.raises(ValueError, match="continuous"):
        engine.run(f, location_id="bengaluru", forcing_source=_source(f))


def test_engine_rejects_empty():
    engine = CoupledSimulationEngine(spinup_days=2)
    src = _source(_forcing(5))  # valid source metadata, but no steps passed to engine
    with pytest.raises(ValueError):
        engine.run([], location_id="bengaluru", forcing_source=src)


def test_engine_rejects_spinup_longer_than_forcing():
    engine = CoupledSimulationEngine(spinup_days=90)
    with pytest.raises(ValueError):
        engine.run(_forcing(50), location_id="bengaluru", forcing_source=_source(_forcing(50)))


def test_engine_provenance_contains_equations_and_sources():
    engine = CoupledSimulationEngine(spinup_days=5)
    run = engine.run(_forcing(100), location_id="bengaluru", forcing_source=_source(_forcing(100)))
    assert len(run.provenance["equations"]) >= 5
    assert run.parameter_sources["cn_ii"]
    assert run.provenance["parameters"]["cn_ii"] == 70.0


def test_run_roundtrip_via_dict():
    engine = CoupledSimulationEngine(spinup_days=5)
    run = engine.run(_forcing(100), location_id="bengaluru", forcing_source=_source(_forcing(100)))
    restored = type(run).from_dict(run.to_dict())
    assert restored.run_id == run.run_id
    assert len(restored.steps) == len(run.steps)
    assert [s.storage_mm for s in restored.steps] == [s.storage_mm for s in run.steps]
