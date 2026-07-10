"""Tests for dashboard.components — cards, filters, sidebar."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestCards:
    """Cover cards.py — metric_card, info_card, status_badge (lines 17, 21, 29-36)."""

    @patch("dashboard.components.cards.st")
    def test_metric_card(self, mock_st):
        from dashboard.components.cards import metric_card

        metric_card("Temperature", 32.5, "+2°C", "The current temperature")
        mock_st.metric.assert_called_once_with(
            label="Temperature", value=32.5, delta="+2°C", help="The current temperature"
        )

    @patch("dashboard.components.cards.st")
    def test_metric_card_no_delta_no_help(self, mock_st):
        from dashboard.components.cards import metric_card

        metric_card("Rainfall", "50mm")
        mock_st.metric.assert_called_once_with(
            label="Rainfall", value="50mm", delta=None, help=None
        )

    @patch("dashboard.components.cards.st")
    def test_info_card(self, mock_st):
        from dashboard.components.cards import info_card

        info_card("Notice", "Some content", icon="ℹ️")
        mock_st.markdown.assert_called_once()
        args, _ = mock_st.markdown.call_args
        assert "Notice" in args[0]
        assert "Some content" in args[0]

    @patch("dashboard.components.cards.st")
    def test_status_badge_active(self, mock_st):
        from dashboard.components.cards import status_badge

        status_badge("Running", "active")
        mock_st.markdown.assert_called_once()
        args, _ = mock_st.markdown.call_args
        assert "#28a745" in args[0]
        assert "Running" in args[0]

    @patch("dashboard.components.cards.st")
    def test_status_badge_inactive(self, mock_st):
        from dashboard.components.cards import status_badge

        status_badge("Stopped", "inactive")
        mock_st.markdown.assert_called_once()
        args, _ = mock_st.markdown.call_args
        assert "#dc3545" in args[0]

    @patch("dashboard.components.cards.st")
    def test_status_badge_pending(self, mock_st):
        from dashboard.components.cards import status_badge

        status_badge("Waiting", "pending")
        mock_st.markdown.assert_called_once()
        args, _ = mock_st.markdown.call_args
        assert "#ffc107" in args[0]

    @patch("dashboard.components.cards.st")
    def test_status_badge_completed(self, mock_st):
        from dashboard.components.cards import status_badge

        status_badge("Done", "completed")
        mock_st.markdown.assert_called_once()
        args, _ = mock_st.markdown.call_args
        assert "#17a2b8" in args[0]

    @patch("dashboard.components.cards.st")
    def test_status_badge_unknown(self, mock_st):
        from dashboard.components.cards import status_badge

        status_badge("Unknown", "unknown_status")
        mock_st.markdown.assert_called_once()
        args, _ = mock_st.markdown.call_args
        assert "#6c757d" in args[0]

    @patch("dashboard.components.cards.st")
    def test_status_badge_case_insensitive(self, mock_st):
        from dashboard.components.cards import status_badge

        status_badge("Active", "ACTIVE")
        mock_st.markdown.assert_called_once()
        args, _ = mock_st.markdown.call_args
        assert "#28a745" in args[0]


class TestFilters:
    """Cover filters.py — date_range_filter, horizon_selector, scenario_parameters (lines 14-37)."""

    @patch("dashboard.components.filters.st")
    def test_date_range_filter(self, mock_st):
        from datetime import date, timedelta

        from dashboard.components.filters import date_range_filter

        today = date.today()
        mock_st.date_input.side_effect = [today - timedelta(days=90), today]

        start, end = date_range_filter("test_range", 90)
        assert start == today - timedelta(days=90)
        assert end == today
        assert mock_st.date_input.call_count == 2

    @patch("dashboard.components.filters.st")
    def test_horizon_selector(self, mock_st):
        from dashboard.components.filters import horizon_selector

        mock_st.selectbox.return_value = "3 Days"
        result = horizon_selector("test_horizon")
        assert result == 3
        mock_st.selectbox.assert_called_once()

    @patch("dashboard.components.filters.st")
    def test_scenario_parameters(self, mock_st):
        from dashboard.components.filters import scenario_parameters

        col1 = MagicMock()
        col2 = MagicMock()
        mock_st.columns.return_value = [col1, col2]
        mock_st.slider.side_effect = [2.0, 50]
        result = scenario_parameters()
        assert result["temperature_delta"] == 2.0
        assert result["rainfall_change_pct"] == 50
        assert mock_st.slider.call_count == 2


class TestSidebar:
    """Cover sidebar.py — render_sidebar (lines 3-58, 0%)."""

    @patch("dashboard.components.sidebar.st")
    def test_render_sidebar(self, mock_st):
        from dashboard.components.sidebar import render_sidebar

        mock_st.selectbox.side_effect = [
            "All",
            "Bengaluru Urban (KA-BLR-001)",
            "Rainfall",
            "3-Day",
        ]
        mock_st.sidebar.__enter__.return_value = mock_st

        result = render_sidebar()
        assert result["district"] == "All"
        assert result["location_id"] == "KA-BLR-001"
        assert result["variable"] == "Rainfall"
        assert result["horizon"] == 3
        assert mock_st.sidebar.__enter__.called

    @patch("dashboard.components.sidebar.st")
    def test_render_sidebar_with_district_filter(self, mock_st):
        from dashboard.components.sidebar import render_sidebar

        mock_st.selectbox.side_effect = [
            "Mysuru",
            "Mysuru (KA-MYS-001)",
            "MaxTemp",
            "7-Day",
        ]
        mock_st.sidebar.__enter__.return_value = mock_st

        result = render_sidebar()
        assert result["district"] == "Mysuru"
        assert result["location_id"] == "KA-MYS-001"
        assert result["variable"] == "MaxTemp"
        assert result["horizon"] == 7
