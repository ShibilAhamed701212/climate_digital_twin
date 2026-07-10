"""Tests for dashboard.charts — covering remaining uncovered lines."""

from __future__ import annotations


class TestComparisonGrouped:
    """Cover grouped_comparison (lines 73-92)."""

    def test_grouped_comparison_default_keys(self):
        from dashboard.charts.comparison import grouped_comparison

        data = [
            {"district": "A", "rainfall": 50, "max_temp": 30, "min_temp": 20},
            {"district": "B", "rainfall": 75, "max_temp": 32, "min_temp": 22},
        ]
        fig = grouped_comparison(data)
        assert fig is not None
        assert len(fig.data) == 3
        assert fig.data[0].name == "rainfall"
        assert fig.data[1].name == "max_temp"
        assert fig.data[2].name == "min_temp"

    def test_grouped_comparison_custom_keys(self):
        from dashboard.charts.comparison import grouped_comparison

        data = [
            {"district": "A", "rainfall": 50, "max_temp": 30},
            {"district": "B", "rainfall": 75, "max_temp": 32},
        ]
        fig = grouped_comparison(data, y_keys=["rainfall", "max_temp"], title="Custom")
        assert fig is not None
        assert len(fig.data) == 2
        assert fig.layout.title.text == "Custom"

    def test_grouped_comparison_empty_data_raises(self):
        import pytest

        from dashboard.charts.comparison import grouped_comparison

        with pytest.raises(KeyError):
            grouped_comparison([])

    def test_grouped_comparison_single_item(self):
        from dashboard.charts.comparison import grouped_comparison

        data = [{"district": "A", "rainfall": 50, "max_temp": 30, "min_temp": 20}]
        fig = grouped_comparison(data)
        assert fig is not None
        assert len(fig.data) == 3
