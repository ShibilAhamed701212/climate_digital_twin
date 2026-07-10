"""Tests for simulator/outputs/output_generator.py."""

from __future__ import annotations

import json
import os
import tempfile

from simulator.models.scenario_models import ScenarioDefinition, ScenarioRun, SimulationResult
from simulator.outputs.output_generator import OutputGenerator


class TestOutputGenerator:
    def _make_run(self, location_id: str = "loc-001", success: bool = True) -> ScenarioRun:
        scenario = ScenarioDefinition(
            scenario_id="test-001",
            name="Test Scenario",
            description="Test",
            scenario_type="warming",
            parameters={"temp_delta": 2.0},
        )
        result = SimulationResult(
            location_id=location_id,
            scenario_id="test-001",
            timestamp="2026-01-01T00:00:00",
            baseline={"rainfall": 100.0, "max_temp": 30.0, "min_temp": 20.0},
            simulated={"rainfall": 90.0, "max_temp": 32.0, "min_temp": 22.0},
            deltas={"rainfall": -10.0, "max_temp": 2.0, "min_temp": 2.0},
            duration_ms=100.0,
            success=success,
        )
        return ScenarioRun(
            run_id="run-001",
            scenario=scenario,
            results=[result],
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:00:01",
            total_duration_ms=1234.56,
            location_count=1,
            status="completed",
        )

    def test_init_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "outputs")
            OutputGenerator(out_dir)
            assert os.path.isdir(out_dir)

    def test_init_default_directory(self) -> None:
        gen = OutputGenerator()
        assert gen.output_dir == "simulator/outputs"

    def test_export_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = self._make_run()
            path = gen.export_json(run)
            assert path.endswith(".json")
            assert os.path.isfile(path)
            with open(path) as f:
                data = json.load(f)
            assert data["run_id"] == "run-001"
            assert data["scenario"]["scenario_id"] == "test-001"
            assert len(data["results"]) == 1
            assert data["results"][0]["location_id"] == "loc-001"

    def test_export_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = self._make_run()
            path = gen.export_csv(run)
            assert path.endswith(".csv")
            assert os.path.isfile(path)
            with open(path) as f:
                content = f.read()
            assert "location_id" in content
            assert "loc-001" in content

    def test_export_csv_empty_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = self._make_run()
            # Create a new result with empty deltas (frozen dataclass)
            empty_result = SimulationResult(
                location_id="loc-empty",
                scenario_id="test-001",
                timestamp="2026-01-01T00:00:00",
                baseline={},
                simulated={},
                deltas={},
                duration_ms=0.0,
                success=True,
            )
            run = ScenarioRun(
                run_id=run.run_id,
                scenario=run.scenario,
                results=[empty_result],
                started_at=run.started_at,
                completed_at=run.completed_at,
                total_duration_ms=run.total_duration_ms,
                location_count=1,
                status=run.status,
            )
            path = gen.export_csv(run)
            with open(path) as f:
                content = f.read()
            assert "loc-empty" in content

    def test_export_csv_failed_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = self._make_run(success=False)
            path = gen.export_csv(run)
            with open(path) as f:
                content = f.read()
            assert "False" in content or "false" in content.lower()

    def test_export_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = self._make_run()
            path = gen.export_markdown(run)
            assert path.endswith(".md")
            assert os.path.isfile(path)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "Test Scenario" in content
            assert "run-001" in content
            assert "✅" in content

    def test_export_markdown_failed_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = self._make_run(success=False)
            path = gen.export_markdown(run)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "❌" in content

    def test_export_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gen = OutputGenerator(tmp)
            run = self._make_run()
            paths = gen.export_all(run)
            for fmt in ("json", "csv", "markdown"):
                assert fmt in paths
                assert os.path.isfile(paths[fmt]), f"{fmt} file missing"
