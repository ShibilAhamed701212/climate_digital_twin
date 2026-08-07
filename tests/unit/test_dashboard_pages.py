"""Verify each dashboard page module can be imported without errors.

Streamlit page filenames start with numbers (e.g., 01_climate_overview.py)
which are not valid Python identifiers. Use importlib to load them
from their file path rather than via dot-path imports.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _page_imports_from_file(filepath: str) -> tuple[bool, str]:
    """Check that a Streamlit page file can be imported from its path.

    Args:
        filepath: Relative path from project root to the page file.

    Returns:
        Tuple of (success, error_message).
    """
    full_path = PROJECT_ROOT / filepath
    if not full_path.exists():
        return False, f"File not found: {full_path}"

    sys.path.insert(0, str(PROJECT_ROOT))
    spec = importlib.util.spec_from_file_location("page", str(full_path))
    if spec is None:
        return False, "Could not create module spec"
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return True, ""
    except Exception as e:
        return False, str(e)


def test_climate_overview_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/01_climate_overview.py")
    assert success, f"Climate Overview page failed to import: {msg}"


def test_forecast_viewer_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/02_forecast_viewer.py")
    assert success, f"Forecast Viewer page failed to import: {msg}"


def test_twin_state_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/03_twin_state.py")
    assert success, f"Twin State page failed to import: {msg}"


def test_scenario_simulator_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/04_scenario_simulator.py")
    assert success, f"Scenario Simulator page failed to import: {msg}"


def test_climate_risk_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/05_climate_risk.py")
    assert success, f"Climate Risk page failed to import: {msg}"


def test_reports_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/06_reports.py")
    assert success, f"Reports page failed to import: {msg}"


def test_copilot_chat_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/07_copilot_chat.py")
    assert success, f"Copilot Chat page failed to import: {msg}"


def test_knowledge_base_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/08_knowledge_base.py")
    assert success, f"Knowledge Base page failed to import: {msg}"


def test_spatial_grid_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/09_spatial_grid.py")
    assert success, f"Spatial Grid page failed to import: {msg}"


def test_feedback_page_imports():
    success, msg = _page_imports_from_file("dashboard/page_views/10_feedback.py")
    assert success, f"Feedback page failed to import: {msg}"
