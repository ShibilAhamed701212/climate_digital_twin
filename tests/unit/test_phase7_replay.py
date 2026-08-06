"""Phase 7 — historical replay, isolation, and store/service tests.

These exercise the simulation against REAL data (data/real Bengaluru CSVs and
data/raw grid parquet), assert the documented response experiments (heavy rain,
dry period, temperature -> ET, dry vs wet soil runoff), and verify the store
never touches REAL stores.
"""

from __future__ import annotations

import os

import pytest

from climatedt.simulation.engine import CoupledSimulationEngine
from climatedt.simulation.forcing import load_bengaluru_forcing, load_grid_forcing
from climatedt.simulation.service import SimulationService

_HAVE_REAL = os.path.isdir("data/real") and os.path.isdir("data/raw")

pytestmark = pytest.mark.skipif(
    not _HAVE_REAL,
    reason="requires data/real and data/raw; run with repo data present",
)


def test_bengaluru_replay_bounds_and_balance():
    days, source = load_bengaluru_forcing()
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(days, location_id="bengaluru", forcing_source=source)
    assert len(days) > 500  # multi-year record
    assert len(run.steps) == len(days) - 90
    assert abs(run.mass_balance["residual_mm"]) < 1e-6
    assert all(0.0 <= s.storage_mm <= 150.0 for s in run.steps)
    assert all(0.0 <= s.aet_mm <= 12.0 for s in run.steps)  # ET not absurd
    assert run.provenance["forcing"]["authenticity"] == "REAL"
    assert run.authenticity == "SIMULATED"


def test_bengaluru_dry_period_decreases_storage():
    days, source = load_bengaluru_forcing()
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(days, location_id="bengaluru", forcing_source=source)
    # Find a long no-rain window in the dry season (Jan-Mar) and check storage drops.
    zero_runs = []
    cur = []
    for s in run.steps:
        if s.precipitation_mm == 0.0:
            cur.append(s)
        else:
            if len(cur) >= 14:
                zero_runs.append(cur)
            cur = []
    if len(cur) >= 14:
        zero_runs.append(cur)
    assert zero_runs, "expected at least one 14-day dry spell in record"
    longest = max(zero_runs, key=len)
    assert longest[-1].storage_mm < longest[0].storage_mm
    assert longest[-1].dryness > longest[0].dryness


def test_bengaluru_heavy_rain_increases_storage_quickly():
    days, source = load_bengaluru_forcing()
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(days, location_id="bengaluru", forcing_source=source)
    heaviest = max(run.steps, key=lambda s: s.precipitation_mm)
    assert heaviest.precipitation_mm > 50.0
    # Storage after the heaviest rain exceeds the day before.
    idx = run.steps.index(heaviest)
    if idx > 0:
        assert heaviest.storage_mm >= run.steps[idx - 1].storage_mm


def test_grid_cell_replay_2022_event():
    # 2022-08-18 extreme event cell (12.5N, 78.0E), antecedent ~0.39mm/5d.
    days, source = load_grid_forcing(12.5, 78.0, "2021-06-01", "2023-05-31")
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(days, location_id="grid-12.5-78.0", forcing_source=source)
    event = [s for s in run.steps if s.date == "2022-08-18"]
    assert event, "2022-08-18 must be in the replay window"
    step = event[0]
    assert step.precipitation_mm == pytest.approx(266.32, abs=0.5)
    assert step.runoff_mm > 50.0  # large storm -> substantial runoff


def test_dry_vs_wet_soil_runoff_response():
    # Same storm, dry soil vs wet soil (high antecedent): wet soil must produce
    # more runoff than dry soil.
    from climatedt.simulation.processes.runoff import scs_runoff

    dry = scs_runoff(266.32, 70.0, antecedent_5d_mm=0.39)
    wet = scs_runoff(266.32, 70.0, antecedent_5d_mm=80.0)
    assert wet > dry
    assert wet > 0.0


def test_temperature_increases_et():
    # Same day, hotter: PET must be higher (temperature drives ET).
    from climatedt.simulation.processes.evapotranspiration import hargreaves_et0

    cool = hargreaves_et0(30.0, 20.0, 12.97, 100)
    hot = hargreaves_et0(40.0, 30.0, 12.97, 100)
    assert hot > cool


def test_store_isolation_and_roundtrip(tmp_path):
    from climatedt.simulation.store import SimulationStore

    days, source = load_bengaluru_forcing()
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(days, location_id="bengaluru", forcing_source=source)
    store = SimulationStore(base_dir=str(tmp_path))
    store.save_run(run)
    loaded = store.get_run(run.run_id)
    assert loaded is not None
    assert loaded.run_id == run.run_id
    assert loaded.mass_balance == run.mass_balance
    assert loaded.authenticity == "SIMULATED"


def test_store_save_is_idempotent(tmp_path):
    from climatedt.simulation.store import SimulationStore

    days, source = load_bengaluru_forcing()
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(days, location_id="bengaluru", forcing_source=source)
    store = SimulationStore(base_dir=str(tmp_path))
    store.save_run(run)
    store.save_run(run)  # second save must not duplicate
    assert len(store.list_runs()) == 1


def test_service_runs_bengaluru(tmp_path):
    from climatedt.simulation.store import SimulationStore

    store = SimulationStore(base_dir=str(tmp_path))
    service = SimulationService(store=store)
    run = service.run_bengaluru()
    assert run is not None
    assert len(run.steps) > 400
    loaded = service.get_run(run.run_id)
    assert loaded is not None
    assert loaded.run_id == run.run_id


def test_service_run_ids_are_deterministic(tmp_path):
    from climatedt.simulation.store import SimulationStore

    store = SimulationStore(base_dir=str(tmp_path))
    service = SimulationService(store=store)
    r1 = service.run_bengaluru()
    store2 = SimulationStore(base_dir=str(tmp_path))
    service2 = SimulationService(store=store2)
    r2 = service2.run_bengaluru()
    assert r1.run_id == r2.run_id


def test_simulated_never_writes_to_real_stores(tmp_path):
    """Running simulations must not create/alter ObservationStore, ForecastStore,
    HazardStore, AlertStore, or the REAL twin data dirs."""
    import os

    from climatedt.simulation.store import SimulationStore

    real_dirs = ["data/observations", "data/forecasts", "data/hazards", "data/alerts"]
    before = {d: set(os.listdir(d)) if os.path.isdir(d) else None for d in real_dirs}

    days, source = load_bengaluru_forcing()
    engine = CoupledSimulationEngine(spinup_days=90)
    run = engine.run(days, location_id="bengaluru", forcing_source=source)
    SimulationStore(base_dir=str(tmp_path)).save_run(run)

    after = {d: set(os.listdir(d)) if os.path.isdir(d) else None for d in real_dirs}
    assert before == after
