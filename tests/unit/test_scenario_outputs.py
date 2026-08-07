"""Unit tests for output and report generators."""

from __future__ import annotations

import json
import os
import tempfile

import pytest


class TestOutputGenerator:
    """Test the output file generator."""

    @pytest.fixture
    def output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield tmp

    @pytest.fixture
    def sample_run(self):
        from simulator.models.scenario_models import (
            ScenarioDefinition,
            ScenarioRun,
            SimulationResult,
        )

        scenario = ScenarioDefinition(
            scenario_id="test_001",
            name="Test Scenario",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="test_001",
                timestamp="2024-01-01T00:00:00",
                baseline={"rainfall": 100, "max_temp": 30, "min_temp": 20},
                simulated={"rainfall": 100, "max_temp": 32, "min_temp": 22},
                deltas={"rainfall": 0.0, "max_temp": 2.0, "min_temp": 2.0},
                duration_ms=5.0,
                success=True,
            ),
        ]
        return ScenarioRun(
            run_id="run_001",
            scenario=scenario,
            results=results,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            total_duration_ms=10.0,
            location_count=1,
            status="completed",
        )

    def test_export_json(self, output_dir, sample_run):
        from simulator.outputs.output_generator import OutputGenerator

        gen = OutputGenerator(output_dir=output_dir)
        path = gen.export_json(sample_run)
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["run_id"] == "run_001"
        assert data["scenario"]["scenario_id"] == "test_001"

    def test_export_csv(self, output_dir, sample_run):
        from simulator.outputs.output_generator import OutputGenerator

        gen = OutputGenerator(output_dir=output_dir)
        path = gen.export_csv(sample_run)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "KA-BLR-001" in content
        assert "delta_max_temp" in content

    def test_export_markdown(self, output_dir, sample_run):
        from simulator.outputs.output_generator import OutputGenerator

        gen = OutputGenerator(output_dir=output_dir)
        path = gen.export_markdown(sample_run)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "Scenario Simulation Report" in content
        assert "KA-BLR-001" in content

    def test_export_all(self, output_dir, sample_run):
        from simulator.outputs.output_generator import OutputGenerator

        gen = OutputGenerator(output_dir=output_dir)
        paths = gen.export_all(sample_run)
        assert "json" in paths
        assert "csv" in paths
        assert "markdown" in paths
        for fmt, path in paths.items():
            assert os.path.exists(path), f"Missing {fmt} output: {path}"


class TestReportGenerator:
    """Test the report generator."""

    @pytest.fixture
    def output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield tmp

    @pytest.fixture
    def sample_run(self):
        from simulator.models.scenario_models import (
            ScenarioDefinition,
            ScenarioRun,
            SimulationResult,
        )

        scenario = ScenarioDefinition(
            scenario_id="test_001",
            name="Test Scenario",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="test_001",
                timestamp="2024-01-01T00:00:00",
                baseline={"rainfall": 100, "max_temp": 30, "min_temp": 20},
                simulated={"rainfall": 100, "max_temp": 32, "min_temp": 22},
                deltas={"rainfall": 0.0, "max_temp": 2.0, "min_temp": 2.0},
                duration_ms=5.0,
                success=True,
            ),
        ]
        return ScenarioRun(
            run_id="run_001",
            scenario=scenario,
            results=results,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            total_duration_ms=10.0,
            location_count=1,
            status="completed",
        )

    def test_generate_summary(self, sample_run):
        from simulator.reports.report_generator import ReportGenerator

        gen = ReportGenerator()
        summary = gen.generate_summary(sample_run)
        assert summary["run_id"] == "run_001"
        assert summary["total_locations"] == 1
        assert summary["successful_locations"] == 1
        assert "aggregate_deltas" in summary

    def test_generate_markdown_report(self, output_dir, sample_run):
        from simulator.reports.report_generator import ReportGenerator

        gen = ReportGenerator(output_dir=output_dir)
        path = gen.generate_markdown_report(sample_run)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "Climate Impact Report" in content
        assert "Test Scenario" in content
        assert "max_temp" in content

    def test_aggregate_deltas(self, sample_run):
        from simulator.reports.report_generator import ReportGenerator

        agg = ReportGenerator._aggregate_deltas(sample_run)
        assert "rainfall" in agg
        assert "max_temp" in agg
        assert agg["max_temp"]["avg"] == 2.0

    def test_failed_result_excluded(self):
        from simulator.models.scenario_models import (
            ScenarioDefinition,
            ScenarioRun,
            SimulationResult,
        )
        from simulator.reports.report_generator import ReportGenerator

        scenario = ScenarioDefinition(
            scenario_id="test",
            name="",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="test",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={},
                deltas={},
                duration_ms=1.0,
                success=False,
                error_message="fail",
            ),
        ]
        run = ScenarioRun(
            run_id="run_fail",
            scenario=scenario,
            results=results,
            started_at="",
            completed_at="",
            total_duration_ms=1.0,
            location_count=1,
            status="completed",
        )
        agg = ReportGenerator._aggregate_deltas(run)
        assert agg == {}
