"""Tests for dashboard.app.py — configuration, page loading, initialization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_streamlit():
    """Mock streamlit before any app module import."""
    mock_st = MagicMock()
    mock_st.session_state = MagicMock()
    mock_st.session_state.__contains__.return_value = False

    with patch.dict("sys.modules", {"streamlit": mock_st}):
        yield mock_st


class TestAppLoadCSS:
    """Cover _load_css (lines 16-22)."""

    def test_load_css_found(self, _mock_streamlit):
        import dashboard.app

        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "body { color: red; }"

        with patch("builtins.open", return_value=mock_file):
            dashboard.app._load_css()
            _mock_streamlit.markdown.assert_called_once_with(
                "<style>body { color: red; }</style>", unsafe_allow_html=True
            )

    def test_load_css_not_found(self, _mock_streamlit):
        import dashboard.app

        with patch("builtins.open", side_effect=FileNotFoundError):
            dashboard.app._load_css()
            _mock_streamlit.markdown.assert_not_called()


class TestAppInitSession:
    """Cover _init_session (lines 24-29)."""

    def test_init_session_sets_api_and_page(self, _mock_streamlit):
        import dashboard.app

        _mock_streamlit.session_state.__contains__.return_value = False
        dashboard.app._init_session()
        assert _mock_streamlit.session_state.api is not None
        assert _mock_streamlit.session_state.page == "01_climate_overview"

    def test_init_session_preserves_existing(self, _mock_streamlit):
        import dashboard.app

        existing_api = MagicMock()
        _mock_streamlit.session_state.__contains__.side_effect = lambda k: k in ["api", "page"]
        _mock_streamlit.session_state.api = existing_api
        _mock_streamlit.session_state.page = "05_climate_risk"

        dashboard.app._init_session()
        assert _mock_streamlit.session_state.api is existing_api
        assert _mock_streamlit.session_state.page == "05_climate_risk"


class TestAppMain:
    """Cover main() (lines 31-71)."""

    def _import_side_effect(self, pages_module):
        def side_effect(name, *args, **kwargs):
            if name.startswith("dashboard.page_views."):
                return pages_module
            return __import__(name, *args, **kwargs)

        return side_effect

    def test_main_successful_load(self, _mock_streamlit):
        import dashboard.app

        page_module = MagicMock()
        page_module.render = MagicMock()

        with (
            patch("builtins.__import__", self._import_side_effect(page_module)),
            patch("dashboard.app.render_sidebar", return_value={}),
            patch("dashboard.app.render_sidebar_nav", return_value=None),
        ):
            dashboard.app.main()

        _mock_streamlit.set_page_config.assert_called_once()
        page_module.render.assert_called_once()

    def test_main_page_not_found(self, _mock_streamlit):
        import dashboard.app

        def import_side(name, *args, **kwargs):
            if name.startswith("dashboard.page_views."):
                raise ImportError("No module named 'x'")
            return __import__(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=import_side),
            patch("dashboard.app.render_sidebar", return_value={}),
            patch("dashboard.app.render_sidebar_nav", return_value=None),
        ):
            dashboard.app.main()

        import dashboard.app as app_mod

        app_mod.st.error.assert_called_once()

    def test_main_with_existing_session(self, _mock_streamlit):
        existing_api = MagicMock()
        _mock_streamlit.session_state.__contains__.side_effect = lambda k: k in ["api", "page"]
        _mock_streamlit.session_state.api = existing_api
        _mock_streamlit.session_state.page = "03_twin_state"
        import dashboard.app

        page_module = MagicMock()
        page_module.render = MagicMock()

        with (
            patch("builtins.__import__", self._import_side_effect(page_module)),
            patch("dashboard.app.render_sidebar", return_value={}),
            patch("dashboard.app.render_sidebar_nav", return_value=None),
        ):
            dashboard.app.main()

        assert _mock_streamlit.session_state.api is existing_api
        page_module.render.assert_called_once()
        assert _mock_streamlit.session_state.page == "03_twin_state"

    def test_main_render_sidebar_called(self, _mock_streamlit):
        import dashboard.app

        page_module = MagicMock()
        page_module.render = MagicMock()

        with (
            patch("dashboard.app.render_sidebar", return_value={"test": "value"}) as mock_rs,
            patch("dashboard.app.render_sidebar_nav", return_value=None),
            patch("builtins.__import__", self._import_side_effect(page_module)),
        ):
            dashboard.app.main()
            mock_rs.assert_called_once()
            page_module.render.assert_called_once_with(
                _mock_streamlit.session_state.api, {"test": "value"}
            )
