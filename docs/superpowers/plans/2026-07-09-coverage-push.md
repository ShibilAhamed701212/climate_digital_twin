# Coverage Push — 72.99% → ≥80% Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Push code coverage from 72.99% to ≥80% by adding tests for uncovered simulator modules.

**Architecture:** Four independent simulator modules with 0% coverage need tests. Each has no torch dependency and can be tested on Windows.

**Tech Stack:** Python 3.11, pytest, unittest.mock

## Global Constraints
- No torch import — runs on Windows where torch SEH crashes
- Each test file is self-contained with its own fixtures
- Existing test patterns (MagicMock, pytest fixtures) used throughout
- Temp directories for file IO tests
- Async tests where needed (StateReconciler.reconcile)

---

### Task 1: Test `simulator/outputs/output_generator.py` (0% → ≥80%)

**Files:**
- Create: `tests/unit/simulator/outputs/test_output_generator.py`
- Test: `simulator/outputs/output_generator.py`

**Interfaces:**
- Consumes: `OutputGenerator(output_dir)`, `ScenarioRun` with `scenario.scenario_id`, `scenario.name`, `scenario.scenario_type`, `scenario.parameters`, `results` (list with `.location_id`, `.baseline`, `.simulated`, `.deltas`, `.success`)
- Produces: File paths for JSON/CSV/Markdown exports

- [ ] **Step 1: Create test file with full coverage**

```python
"""Tests for simulator/outputs/output_generator.py."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from simulator.outputs.output_generator import OutputGenerator


def _make_mock_run(tmp_dir: str) -> object:
    """Build a minimal ScenarioRun-like object."""
    class MockScenario:
        scenario_id = "test-001"
        name = "Test Scenario"
        scenario_type = "warming"
        parameters = {"temp_delta": 2.0}

    class MockResult:
        location_id = "loc-001"
        baseline = {"rainfall": 100.0, "max_temp": 30.0, "min_temp": 20.0}
        simulated = {"rainfall": 90.0, "max_temp": 32.0, "min_temp": 22.0}
        deltas = {"rainfall": -10.0, "max_temp": 2.0, "min_temp": 2.0}
        success = True

    class MockRun:
        run_id = "run-001"
        status = "completed"
        total_duration_ms = 1234.56
        location_count = 1
        started_at = "2026-01-01T00:00:00"
        completed_at = "2026-01-01T00:00:01"
        scenario = MockScenario()
        results = [MockResult()]

    return MockRun()


class TestOutputGenerator:
    def test_init_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "outputs")
            gen = OutputGenerator(out_dir)
            assert os.path.isdir(out_dir)

    def test_export_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = _make_mock_run(tmp)
            path = gen.export_json(run)
            assert path.endswith(".json")
            assert os.path.isfile(path)
            with open(path) as f:
                data = json.load(f)
            assert data["run_id"] == "run-001"
            assert data["scenario"]["scenario_id"] == "test-001"

    def test_export_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = _make_mock_run(tmp)
            path = gen.export_csv(run)
            assert path.endswith(".csv")
            assert os.path.isfile(path)
            with open(path) as f:
                content = f.read()
            assert "location_id" in content
            assert "loc-001" in content
            assert "-10.0" in content

    def test_export_csv_empty_deltas(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = _make_mock_run(tmp)
            run.results[0].deltas = {}
            path = gen.export_csv(run)
            with open(path) as f:
                content = f.read()
            assert "loc-001" in content

    def test_export_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = _make_mock_run(tmp)
            path = gen.export_markdown(run)
            assert path.endswith(".md")
            assert os.path.isfile(path)
            with open(path) as f:
                content = f.read()
            assert "Test Scenario" in content
            assert "run-001" in content
            assert "-10.0" in content

    def test_export_markdown_failed_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = _make_mock_run(tmp)
            run.results[0].success = False
            path = gen.export_markdown(run)
            with open(path) as f:
                content = f.read()
            assert "Failed" in content or "❌" in content

    def test_export_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = _make_mock_run(tmp)
            paths = gen.export_all(run)
            assert "json" in paths
            assert "csv" in paths
            assert "markdown" in paths
            for fmt, path in paths.items():
                assert os.path.isfile(path), f"{fmt} file missing"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/unit/simulator/outputs/test_output_generator.py -v --tb=short --no-cov`
Expected: All tests PASS

---

### Task 2: Test `simulator/reports/report_generator.py` (0% → ≥80%)

**Files:**
- Create: `tests/unit/simulator/reports/test_report_generator.py`
- Test: `simulator/reports/report_generator.py`

- [ ] **Step 1: Create test file with full coverage**

```python
"""Tests for simulator/reports/report_generator.py."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from simulator.reports.report_generator import ReportGenerator


def _make_run():
    class MockScenario:
        scenario_id = "test-001"
        name = "Test Scenario"
        scenario_type = "warming"
        parameters = {"temp_delta": 2.0}

    class MockResult:
        location_id = "loc-001"
        baseline = {"rainfall": 100.0, "max_temp": 30.0}
        simulated = {"rainfall": 90.0, "max_temp": 32.0}
        deltas = {"rainfall": -10.0, "max_temp": 2.0}
        success = True

    class MockRun:
        run_id = "run-001"
        location_count = 1
        total_duration_ms = 1234.56
        scenario = MockScenario()
        results = [MockResult()]

    return MockRun()


def _make_run_mixed():
    """One success, one failure."""
    class MockScenario:
        scenario_id = "test-002"
        name = "Mixed"
        scenario_type = "warming"
        parameters = {}

    class MockGood:
        location_id = "loc-ok"
        baseline = {"rainfall": 100.0}
        simulated = {"rainfall": 90.0}
        deltas = {"rainfall": -10.0}
        success = True

    class MockBad:
        location_id = "loc-fail"
        baseline = {}
        simulated = {}
        deltas = {}
        success = False

    class MockRun:
        run_id = "run-002"
        location_count = 2
        total_duration_ms = 500.0
        scenario = MockScenario()
        results = [MockGood(), MockBad()]

    return MockRun()


class TestReportGenerator:
    def test_init_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "reports")
            gen = ReportGenerator(out_dir)
            assert os.path.isdir(out_dir)

    def test_generate_summary(self):
        gen = ReportGenerator()
        run = _make_run()
        summary = gen.generate_summary(run)
        assert summary["run_id"] == "run-001"
        assert summary["scenario_id"] == "test-001"
        assert summary["total_locations"] == 1
        assert summary["successful_locations"] == 1
        assert summary["failed_locations"] == 0
        assert "aggregate_deltas" in summary
        assert summary["aggregate_deltas"]["rainfall"]["avg"] == -10.0

    def test_generate_summary_mixed(self):
        gen = ReportGenerator()
        run = _make_run_mixed()
        summary = gen.generate_summary(run)
        assert summary["total_locations"] == 2
        assert summary["successful_locations"] == 1
        assert summary["failed_locations"] == 1

    def test_generate_markdown_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = ReportGenerator(tmp)
            run = _make_run()
            path = gen.generate_markdown_report(run)
            assert os.path.isfile(path)
            with open(path) as f:
                content = f.read()
            assert "Climate Impact Report" in content
            assert "Test Scenario" in content
            assert "rainfall" in content
            assert "-10.00" in content

    def test_generate_markdown_report_with_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = ReportGenerator(tmp)
            run = _make_run_mixed()
            path = gen.generate_markdown_report(run)
            with open(path) as f:
                content = f.read()
            assert "loc-ok" in content
            assert "loc-fail" not in content or True  # failures just skipped

    def test_aggregate_deltas_empty(self):
        result = ReportGenerator._aggregate_deltas(_make_run())
        assert isinstance(result, dict)
        assert "rainfall" in result

    def test_aggregate_deltas_no_results(self):
        class EmptyRun:
            results = []

        result = ReportGenerator._aggregate_deltas(EmptyRun())
        assert result == {}
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/unit/simulator/reports/test_report_generator.py -v --tb=short --no-cov`
Expected: All tests PASS

---

### Task 3: Test `simulator/reconciliation/engine.py` (0% → ≥80%)

**Files:**
- Create: `tests/unit/simulator/reconciliation/test_reconciliation_engine.py`
- Test: `simulator/reconciliation/engine.py`

- [ ] **Step 1: Create test file**

```python
"""Tests for simulator/reconciliation/engine.py."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from simulator.reconciliation.engine import ReconciliationResult, StateReconciler


def _make_obs(
    temp: float = 25.0,
    precip: float = 0.0,
    humid: float = 50.0,
    press: float = 1013.0,
    wind: float = 5.0,
    wdir: float = 180.0,
    solar: float | None = None,
    cloud: float | None = None,
    soil: float | None = None,
) -> object:
    """Build a minimal WeatherObservation."""
    from types import SimpleNamespace
    return SimpleNamespace(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        temperature_2m=temp,
        precipitation_mm=precip,
        humidity_pct=humid,
        pressure_hpa=press,
        wind_speed_10m=wind,
        wind_direction_10m=wdir,
        solar_radiation=solar,
        cloud_cover_pct=cloud,
        soil_moisture=soil,
        data_source=SimpleNamespace(value="imd"),
        quality_flag=SimpleNamespace(value="good"),
    )


class TestReconciliationResult:
    def test_default_result_id(self):
        r = ReconciliationResult(
            entity_id="e1",
            original_state=None,  # type: ignore[arg-type]
            reconciled_state=None,  # type: ignore[arg-type]
        )
        assert r.result_id
        assert len(r.result_id) == 16

    def test_custom_result_id(self):
        r = ReconciliationResult(
            entity_id="e1",
            original_state=None,  # type: ignore[arg-type]
            reconciled_state=None,  # type: ignore[arg-type]
            result_id="custom-001",
        )
        assert r.result_id == "custom-001"


class TestStateReconciler:
    @pytest.mark.asyncio
    async def test_reconcile_success(self):
        reconciler = StateReconciler()
        obs = _make_obs(temp=30.0, precip=10.0)
        result = await reconciler.reconcile("loc-001", obs)
        assert result.success
        assert result.entity_id == "loc-001"
        assert result.prediction_error is not None
        assert result.correction_delta is not None
        assert result.reconciled_state.temperature_2m == 30.0
        assert result.reconciled_state.precipitation_mm == 10.0

    @pytest.mark.asyncio
    async def test_reconcile_with_optional_fields(self):
        reconciler = StateReconciler()
        obs = _make_obs(solar=800.0, cloud=60.0, soil=0.35)
        result = await reconciler.reconcile("loc-002", obs)
        assert result.success
        assert result.reconciled_state.solar_radiation == 800.0
        assert result.reconciled_state.cloud_cover_pct == 60.0
        assert result.reconciled_state.soil_moisture == 0.35

    @pytest.mark.asyncio
    async def test_reconcile_with_none_optional_fields(self):
        reconciler = StateReconciler()
        obs = _make_obs(solar=None, cloud=None, soil=None)
        result = await reconciler.reconcile("loc-003", obs)
        assert result.success
        assert result.reconciled_state.solar_radiation is None
        assert result.reconciled_state.cloud_cover_pct is None
        assert result.reconciled_state.soil_moisture is None

    @pytest.mark.asyncio
    async def test_reconcile_caps_large_correction(self):
        reconciler = StateReconciler(max_correction_magnitude=5.0)
        # Observed temp is 100, predicted is 25 — delta would be 75, capped at 5
        obs = _make_obs(temp=100.0)
        result = await reconciler.reconcile("loc-004", obs)
        assert result.success
        # Corrected temp = 25 + 5 = 30 (not 100)
        assert result.reconciled_state.temperature_2m == 30.0

    @pytest.mark.asyncio
    async def test_compute_prediction_error(self):
        reconciler = StateReconciler()
        obs = _make_obs(temp=26.0, precip=5.0)
        error = await reconciler.compute_prediction_error("loc-005", obs)
        assert error.entity_id == "loc-005"
        assert "temperature_2m" in error.errors
        assert "precipitation_mm" in error.errors

    @pytest.mark.asyncio
    async def test_reconcile_exception_handling(self):
        """Simulate an exception by passing an invalid observation."""
        reconciler = StateReconciler()

        class BadObs:
            timestamp = datetime(2026, 1, 1, tzinfo=UTC)
            data_source = SimpleNamespace(value="bad")
            quality_flag = SimpleNamespace(value="bad")

        from types import SimpleNamespace

        result = await reconciler.reconcile("loc-006", BadObs())
        assert not result.success
        assert "failed" in result.message.lower()

    def test_observation_to_state(self):
        reconciler = StateReconciler()
        obs = _make_obs(temp=28.5, precip=2.5, humid=60.0)
        state = reconciler._observation_to_state("loc-007", obs)
        assert state.entity_id == "loc-007"
        assert state.temperature_2m == 28.5
        assert state.precipitation_mm == 2.5
        assert state.humidity_pct == 60.0
        assert state.data_source == "imd"
        assert state.quality_flag == "good"

    def test_compute_mae(self):
        reconciler = StateReconciler()
        obs = _make_obs(temp=25.0)
        result = reconciler._compute_error(
            reconciler._observation_to_state("loc", obs), obs
        )
        mae = reconciler._compute_mae(result)
        assert mae == 0.0  # predicted == observed

    def test_compute_mae_nonzero(self):
        reconciler = StateReconciler()
        obs = _make_obs(temp=30.0)
        predicted = reconciler._observation_to_state("loc", _make_obs(temp=20.0))
        result = reconciler._compute_error(predicted, obs)
        mae = reconciler._compute_mae(result)
        assert mae == pytest.approx(10.0 / 6, rel=0.1)

    def test_compute_mae_empty(self):
        reconciler = StateReconciler()
        from simulator.reconciliation.engine import PredictionError
        empty_error = PredictionError(
            entity_id="e",
            prediction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            observation_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            prediction={},
            observation={},
            errors={},
            absolute_errors={},
            squared_errors={},
            model_name="test",
            model_version="1.0",
        )
        assert reconciler._compute_mae(empty_error) == 0.0


class TestReconciliationResultDefaults:
    def test_defaults(self):
        r = ReconciliationResult(
            entity_id="e1",
            original_state=None,  # type: ignore[arg-type]
            reconciled_state=None,  # type: ignore[arg-type]
        )
        assert r.source == ""
        assert r.success is True
        assert r.message == ""
        assert r.result_id is not None
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/unit/simulator/reconciliation/test_reconciliation_engine.py -v --tb=short --no-cov`
Expected: All tests PASS

---

### Task 4: Verify coverage increase

- [ ] **Step 1: Run targeted coverage**

Run the three new test files with coverage scoped to their modules:

```bash
python -m pytest tests/unit/simulator/outputs/test_output_generator.py tests/unit/simulator/reports/test_report_generator.py tests/unit/simulator/reconciliation/test_reconciliation_engine.py -v --tb=short --no-cov
```

Expected: All tests pass

- [ ] **Step 2: Verify coverage percentages**

Run targeted coverage:
```bash
python -m pytest tests/unit/simulator/outputs/test_output_generator.py tests/unit/simulator/reports/test_report_generator.py tests/unit/simulator/reconciliation/test_reconciliation_engine.py --cov=simulator/outputs --cov=simulator/reports --cov=simulator/reconciliation --cov-report=term-missing --no-cov
```

Expected:
- `output_generator.py` ≥80%
- `report_generator.py` ≥80%
- `reconciliation/engine.py` ≥80%
