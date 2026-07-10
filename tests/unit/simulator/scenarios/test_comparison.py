"""Unit tests for simulator/scenarios/comparison.py."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from simulator.models.scenario_models import SimulationResult


@pytest.fixture
def baseline_result():
    return SimulationResult(
        location_id="KA-BLR-001",
        scenario_id="baseline",
        timestamp="2024-01-01T00:00:00",
        baseline={},
        simulated={
            "time_series": {
                "temperature_2m": [28.0, 30.0, 32.0, 29.0],
                "precipitation_mm": [10.0, 20.0, 15.0, 5.0],
            }
        },
        deltas={},
        duration_ms=1.0,
        success=True,
    )


@pytest.fixture
def scenario_result():
    return SimulationResult(
        location_id="KA-BLR-001",
        scenario_id="scenario",
        timestamp="2024-01-01T00:00:00",
        baseline={},
        simulated={
            "time_series": {
                "temperature_2m": [30.0, 32.0, 34.0, 31.0],
                "precipitation_mm": [12.0, 22.0, 17.0, 7.0],
            }
        },
        deltas={},
        duration_ms=1.0,
        success=True,
    )


class TestSimulationComparisonDefaults:
    def test_default_id_generated(self):
        from simulator.scenarios.comparison import SimulationComparison

        comp = SimulationComparison()
        assert len(comp.comparison_id) == 16


class TestScenarioComparison:
    @pytest.fixture
    def comparer(self):
        from simulator.scenarios.comparison import ScenarioComparison

        return ScenarioComparison()

    def test_compare_baseline_scenario(self, comparer, baseline_result, scenario_result):
        comp = comparer.compare_baseline_scenario(baseline_result, scenario_result)
        assert comp.location_id == "KA-BLR-001"
        assert comp.baseline_result_id == "baseline"
        assert comp.scenario_result_id == "scenario"
        assert "temperature_2m" in comp.variable_deltas
        assert "precipitation_mm" in comp.variable_deltas
        assert comp.variable_deltas["temperature_2m"]["mean"] == 2.0
        assert comp.variable_deltas["precipitation_mm"]["mean"] == 2.0
        assert comp.percentage_changes["temperature_2m"] == pytest.approx(
            ((31.75 - 29.75) / 29.75) * 100.0
        )

    def test_compare_location_mismatch(self, comparer, baseline_result):

        other = SimulationResult(
            location_id="KA-MYS-001",
            scenario_id="scenario",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        with pytest.raises(ValueError, match="Location mismatch"):
            comparer.compare_baseline_scenario(baseline_result, other)

    def test_compare_partial_variables(self, comparer, baseline_result):
        from simulator.scenarios.comparison import SimulationResult as SR  # noqa: N817

        scenario = SR(
            location_id="KA-BLR-001",
            scenario_id="partial",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={"time_series": {"temperature_2m": [30.0, 32.0, 34.0, 31.0]}},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        comp = comparer.compare_baseline_scenario(baseline_result, scenario)
        assert "temperature_2m" in comp.variable_deltas
        assert "precipitation_mm" not in comp.variable_deltas

    def test_compare_no_time_series(self, comparer):
        from simulator.scenarios.comparison import SimulationResult as SR  # noqa: N817

        baseline = SR(
            location_id="KA-BLR-001",
            scenario_id="base",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        scenario = SR(
            location_id="KA-BLR-001",
            scenario_id="scen",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        comp = comparer.compare_baseline_scenario(baseline, scenario)
        assert comp.variable_deltas == {}
        assert comp.percentage_changes == {}
        assert comp.summary == "No variable changes detected."

    def test_compare_short_series_no_significance(self, comparer):
        from simulator.scenarios.comparison import SimulationResult as SR  # noqa: N817

        baseline_short = SR(
            location_id="KA-BLR-001",
            scenario_id="baseline",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={"time_series": {"temperature_2m": [28.0, 30.0]}},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        scenario = SR(
            location_id="KA-BLR-001",
            scenario_id="short",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={"time_series": {"temperature_2m": [30.0, 32.0]}},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        comp = comparer.compare_baseline_scenario(baseline_short, scenario)
        assert "temperature_2m" in comp.variable_deltas

    def test_compare_multiple(self, comparer, baseline_result, scenario_result):
        from simulator.scenarios.comparison import SimulationResult as SR  # noqa: N817

        scenario2 = SR(
            location_id="KA-BLR-001",
            scenario_id="scenario2",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={
                "time_series": {
                    "temperature_2m": [32.0, 34.0, 36.0, 33.0],
                }
            },
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        results = {"base": baseline_result, "sc1": scenario_result, "sc2": scenario2}
        comparisons = comparer.compare_multiple(results)
        assert len(comparisons) == 2
        assert "base_vs_sc1" in comparisons
        assert "base_vs_sc2" in comparisons

    def test_compare_multiple_less_than_two(self, comparer, baseline_result):
        with pytest.raises(ValueError, match="Need at least 2 results"):
            comparer.compare_multiple({"only": baseline_result})

    def test_compute_percentage_changes(self, comparer):
        baseline = {"temperature_2m": 30.0, "precipitation_mm": 100.0}
        scenario = {"temperature_2m": 33.0, "precipitation_mm": 120.0}
        changes = comparer.compute_percentage_changes(baseline, scenario)
        assert changes["temperature_2m"] == 10.0
        assert changes["precipitation_mm"] == 20.0

    def test_compute_percentage_changes_zero_division(self, comparer):
        changes = comparer.compute_percentage_changes(
            {"temp": 0.0, "rain": 0.0},
            {"temp": 0.0, "rain": 5.0},
        )
        assert changes["temp"] == 0.0
        assert changes["rain"] == float("inf")

    def test_significance_test(self, comparer):
        baseline = np.random.default_rng(42).normal(30, 2, 100)
        scenario = np.random.default_rng(42).normal(32, 2, 100)
        result = comparer.significance_test(baseline, scenario, alpha=0.05)
        assert isinstance(result, bool)

    def test_significance_test_short_series(self, comparer):
        assert comparer.significance_test(np.array([1.0]), np.array([2.0])) is False

    def test_generate_comparison_report_empty(self, comparer):
        report = comparer.generate_comparison_report([])
        assert report["num_comparisons"] == 0

    def test_generate_comparison_report(self, comparer, baseline_result, scenario_result):
        comp = comparer.compare_baseline_scenario(baseline_result, scenario_result)
        report = comparer.generate_comparison_report([comp])
        assert report["num_comparisons"] == 1
        assert "variable_summary" in report
        assert "temperature_2m" in report["variable_summary"]
        assert "precipitation_mm" in report["variable_summary"]

    def test_generate_summary_text(self, comparer):  # noqa: ARG002
        from simulator.scenarios.comparison import ScenarioComparison

        text = ScenarioComparison._generate_summary_text(
            {"temp": {"mean": 2.0, "min": 1.0, "max": 3.0}},
            {"temp": 6.67},
            ["temp"],
        )
        assert "temp" in text
        assert "significant" in text

    def test_generate_summary_text_no_vars(self, comparer):  # noqa: ARG002
        from simulator.scenarios.comparison import ScenarioComparison

        text = ScenarioComparison._generate_summary_text({}, {}, [])
        assert text == "No variable changes detected."

    def test_compare_pct_change_zero_base_mean(self, comparer, baseline_result):  # noqa: ARG002
        from simulator.scenarios.comparison import SimulationResult as SR  # noqa: N817

        zero_base = SR(
            location_id="KA-BLR-001",
            scenario_id="zero",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={"time_series": {"temperature_2m": [0.0, 0.0, 0.0, 0.0]}},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        scenario = SR(
            location_id="KA-BLR-001",
            scenario_id="scen",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={"time_series": {"temperature_2m": [1.0, 2.0, 3.0, 4.0]}},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        comp = comparer.compare_baseline_scenario(zero_base, scenario)
        assert comp.percentage_changes.get("temperature_2m") == float("inf")

    def test_ttest_ind_exception(self, comparer):
        from unittest.mock import patch

        from simulator.scenarios.comparison import SimulationResult as SR

        base = SR(
            location_id="KA-BLR-001",
            scenario_id="base",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={"time_series": {"temperature_2m": [25.0] * 30}},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        scen = SR(
            location_id="KA-BLR-001",
            scenario_id="scen",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={"time_series": {"temperature_2m": [26.0] * 30}},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        with patch("scipy.stats.ttest_ind", side_effect=ValueError("test error")):
            comp = comparer.compare_baseline_scenario(base, scen)
        assert "temperature_2m" not in comp.significant_variables

    def test_ttest_ind_significant(self, comparer):
        import numpy as np

        from simulator.scenarios.comparison import SimulationResult as SR

        base = SR(
            location_id="KA-BLR-001",
            scenario_id="base",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={
                "time_series": {"temperature_2m": list(np.random.default_rng(42).normal(30, 1, 30))}
            },
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        scen = SR(
            location_id="KA-BLR-001",
            scenario_id="scen",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={
                "time_series": {"temperature_2m": list(np.random.default_rng(42).normal(35, 1, 30))}
            },
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        comp = comparer.compare_baseline_scenario(base, scen)
        assert "temperature_2m" in comp.significant_variables
        assert comp.variable_deltas["temperature_2m"]["mean"] > 0

    def test_significance_test_mannwhitneyu_error(self, comparer):
        with patch("scipy.stats.mannwhitneyu", side_effect=ValueError("test error")):
            result = comparer.significance_test(
                np.array([1.0, 2.0, 3.0]), np.array([4.0, 5.0, 6.0])
            )
        assert result is False

    def test_generate_comparison_report_with_significant(
        self, comparer, baseline_result, scenario_result
    ):
        comp = comparer.compare_baseline_scenario(baseline_result, scenario_result)
        comp.significant_variables = ["temperature_2m"]
        report = comparer.generate_comparison_report([comp])
        assert report["num_comparisons"] == 1
        assert len(report["key_findings"]) == 1
        assert "Statistically significant" in report["key_findings"][0]

    def test_generate_comparison_report_all_significant(
        self, comparer, baseline_result, scenario_result
    ):
        comp = comparer.compare_baseline_scenario(baseline_result, scenario_result)
        comp.significant_variables = ["temperature_2m", "precipitation_mm"]
        report = comparer.generate_comparison_report([comp])
        assert len(report["key_findings"]) == 2
