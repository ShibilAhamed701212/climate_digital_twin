"""Tests for dashboard.maps — covering uncovered lines."""

from __future__ import annotations


class TestClimateMapValueColor:
    """Cover _value_color else branch (lines 122, 125-137)."""

    def test_value_color_temperature_low(self):
        from dashboard.maps.climate_map import _value_color

        result = _value_color(15, "MaxTemp")
        assert result == "#ffcccc"

    def test_value_color_temperature_medium(self):
        from dashboard.maps.climate_map import _value_color

        result = _value_color(25, "MaxTemp")
        assert result == "#ff6666"

    def test_value_color_temperature_high(self):
        from dashboard.maps.climate_map import _value_color

        result = _value_color(35, "MaxTemp")
        assert result == "#cc0000"

    def test_value_color_temperature_extreme(self):
        from dashboard.maps.climate_map import _value_color

        result = _value_color(50, "MaxTemp")
        assert result == "#660000"

    def test_value_color_temperature_exact_boundary_low(self):
        from dashboard.maps.climate_map import _value_color

        assert _value_color(20, "MaxTemp") == "#ff6666"
        assert _value_color(30, "MaxTemp") == "#cc0000"
        assert _value_color(40, "MaxTemp") == "#660000"


class TestClimateMapValueColorRainfall:
    """Cover _value_color rainfall branches (lines 122, 125-128)."""

    def test_rainfall_low(self):
        from dashboard.maps.climate_map import _value_color

        assert _value_color(10, "Rainfall") == "#b3d9ff"

    def test_rainfall_medium(self):
        from dashboard.maps.climate_map import _value_color

        assert _value_color(40, "Rainfall") == "#4da6ff"

    def test_rainfall_high(self):
        from dashboard.maps.climate_map import _value_color

        assert _value_color(80, "Rainfall") == "#0066cc"

    def test_rainfall_extreme(self):
        from dashboard.maps.climate_map import _value_color

        assert _value_color(150, "Rainfall") == "#003366"

    def test_rainfall_exact_boundaries(self):
        from dashboard.maps.climate_map import _value_color

        assert _value_color(20, "rainfall") == "#4da6ff"
        assert _value_color(60, "Rainfall") == "#0066cc"
        assert _value_color(100, "Rainfall") == "#003366"


class TestComparisonMapDeltaColor:
    """Cover _delta_color temperature branch (lines 99-102)."""

    def test_delta_color_temperature_increase(self):
        from dashboard.maps.comparison_map import _delta_color

        result = _delta_color(35, 30, "MaxTemp")
        assert result == "#cc0000"

    def test_delta_color_temperature_decrease(self):
        from dashboard.maps.comparison_map import _delta_color

        result = _delta_color(25, 30, "MaxTemp")
        assert result == "#0066cc"

    def test_delta_color_temperature_equal(self):
        from dashboard.maps.comparison_map import _delta_color

        result = _delta_color(30, 30, "MaxTemp")
        assert result == "#0066cc"

    def test_delta_color_rainfall_increase(self):
        from dashboard.maps.comparison_map import _delta_color

        result = _delta_color(60, 30, "Rainfall")
        assert result == "#0066cc"

    def test_delta_color_rainfall_decrease(self):
        from dashboard.maps.comparison_map import _delta_color

        result = _delta_color(20, 30, "Rainfall")
        assert result == "#ff9933"
