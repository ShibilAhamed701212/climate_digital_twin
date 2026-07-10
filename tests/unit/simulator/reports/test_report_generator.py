"""Tests for simulator/reports/report_generator.py."""

from __future__ import annotations

import os
import tempfile

from simulator.models.scenario_models import ScenarioDefinition, ScenarioRun, SimulationResult
from simulator.reports.report_generator import ReportGenerator


def _make_run(success_count: int = 1, fail_count: int = 0) -> ScenarioRun:
    """Create a test ScenarioRun with specified success/failure counts."""
    scenario = ScenarioDefinition(
        scenario_id="test-001",
        name="Test Scenario",
        description="Test",
        scenario_type="warming",
        parameters={"temp_delta": 2.0},
    )
    results: list[SimulationResult] = []
    for i in range(success_count):
        results.append(
            SimulationResult(
                location_id=f"loc-ok-{i}",
                scenario_id="test-001",
                timestamp="2026-01-01T00:00:00",
                baseline={"rainfall": 100.0, "max_temp": 30.0, "min_temp": 20.0},
                simulated={"rainfall": 90.0, "max_temp": 32.0, "min_temp": 22.0},
                deltas={"rainfall": -10.0, "max_temp": 2.0, "min_temp": 2.0},
                duration_ms=100.0,
                success=True,
            )
        )
    for i in range(fail_count):
        results.append(
            SimulationResult(
                location_id=f"loc-fail-{i}",
                scenario_id="test-001",
                timestamp="2026-01-01T00:00:00",
                baseline={},
                simulated={},
                deltas={},
                duration_ms=0.0,
                success=False,
                error_message="Simulation failed",
            )
        )
    return ScenarioRun(
        run_id="run-001",
        scenario=scenario,
        results=results,
        started_at="2026-01-01T00:00:00",
        completed_at="2026-01-01T00:00:01",
        total_duration_ms=1234.56,
        location_count=success_count + fail_count,
        status="completed",
    )


class TestReportGenerator:
    def test_init_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "reports")
            ReportGenerator(out_dir)
            assert os.path.isdir(out_dir)

    def test_init_default_directory(self) -> None:
        gen = ReportGenerator()
        assert gen.output_dir == "simulator/reports"

    def test_generate_summary(self) -> None:
        gen = ReportGenerator()
        run = _make_run(success_count=1)
        summary = gen.generate_summary(run)
        assert summary["run_id"] == "run-001"
        assert summary["scenario_id"] == "test-001"
        assert summary["total_locations"] == 1
        assert summary["successful_locations"] == 1
        assert summary["failed_locations"] == 0
        assert "aggregate_deltas" in summary
        assert "rainfall" in summary["aggregate_deltas"]
        assert summary["aggregate_deltas"]["rainfall"]["avg"] == -10.0
        assert summary["aggregate_deltas"]["rainfall"]["min"] == -10.0
        assert summary["aggregate_deltas"]["rainfall"]["max"] == -10.0

    def test_generate_summary_mixed_results(self) -> None:
        gen = ReportGenerator()
        run = _make_run(success_count=2, fail_count=1)
        summary = gen.generate_summary(run)
        assert summary["total_locations"] == 3
        assert summary["successful_locations"] == 2
        assert summary["failed_locations"] == 1
        assert summary["aggregate_deltas"]["rainfall"]["avg"] == -10.0

    def test_generate_summary_all_failed(self) -> None:
        gen = ReportGenerator()
        run = _make_run(success_count=0, fail_count=2)
        summary = gen.generate_summary(run)
        assert summary["successful_locations"] == 0
        assert summary["failed_locations"] == 2
        assert summary["aggregate_deltas"] == {}

    def test_generate_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = ReportGenerator(tmp)
            run = _make_run(success_count=1)
            path = gen.generate_markdown_report(run)
            assert os.path.isfile(path)
            with open(path) as f:
                content = f.read()
            assert "Climate Impact Report" in content
            assert "Test Scenario" in content
            assert "rainfall" in content
            assert "-10.00" in content
            assert "loc-ok-0" in content
            assert "Test Scenario" in content

    def test_generate_markdown_report_all_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = ReportGenerator(tmp)
            run = _make_run(success_count=0, fail_count=1)
            path = gen.generate_markdown_report(run)
            with open(path) as f:
                content = f.read()
            assert "Climate Impact Report" in content
            assert "Failed" in content or "0" in content

    def test_aggregate_deltas_empty_no_results(self) -> None:
        run = _make_run(success_count=0, fail_count=0)
        agg = ReportGenerator._aggregate_deltas(run)
        assert agg == {}

    def test_aggregate_deltas_single(self) -> None:
        run = _make_run(success_count=1)
        agg = ReportGenerator._aggregate_deltas(run)
        assert set(agg.keys()) == {"rainfall", "max_temp", "min_temp"}
        assert agg["rainfall"]["avg"] == -10.0
        assert agg["max_temp"]["avg"] == 2.0
        assert agg["min_temp"]["avg"] == 2.0

    def test_aggregate_deltas_multiple_results(self) -> None:
        run = _make_run(success_count=3)
        agg = ReportGenerator._aggregate_deltas(run)
        assert agg["rainfall"]["avg"] == -10.0
        assert agg["rainfall"]["min"] == -10.0
        assert agg["rainfall"]["max"] == -10.0

    def test_aggregate_deltas_failures_skipped(self) -> None:
        run = _make_run(success_count=1, fail_count=2)
        agg = ReportGenerator._aggregate_deltas(run)
        assert "rainfall" in agg
        assert "error_message" not in agg
