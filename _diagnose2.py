"""Diagnostic v2: Use AppTest with a mock API that responds instantly."""

import logging
import sys
from unittest.mock import MagicMock, PropertyMock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("diagnose")

# Mock the API client BEFORE importing page modules
import dashboard.services.api_client
from dashboard.config.config import SAMPLE_LOCATIONS

mock_api = MagicMock()


# Make the mock return sensible data instantly (no network calls)
def make_state(loc_id):
    meta = next((loc for loc in SAMPLE_LOCATIONS if loc["id"] == loc_id), SAMPLE_LOCATIONS[0])
    return {
        "location_id": loc_id,
        "latitude": meta["lat"],
        "longitude": meta["lon"],
        "district": meta["district"],
        "timestamp": "2026-07-10T12:00:00",
        "rainfall": 22.5,
        "max_temp": 32.0,
        "min_temp": 21.5,
        "risk_score": 15.0,
        "prediction_confidence": 0.75,
        "state_type": "current",
        "data_source": "synthetic",
    }


def make_forecast(loc_id):
    return [
        {
            "location_id": loc_id,
            "latitude": 12.97,
            "longitude": 77.59,
            "district": "Bengaluru Urban",
            "timestamp": "2026-07-11T12:00:00",
            "rainfall": 8.0,
            "max_temp": 30.0,
            "min_temp": 20.0,
            "prediction_confidence": 0.85,
        },
    ]


def make_historical(loc_id):
    return [
        {
            "location_id": loc_id,
            "timestamp": "2026-06-01T12:00:00",
            "rainfall": 15.0,
            "max_temp": 28.0,
            "min_temp": 19.0,
            "state_type": "historical",
        },
    ]


mock_api.get_all_locations.return_value = SAMPLE_LOCATIONS
mock_api.get_current_state.side_effect = lambda loc_id: make_state(loc_id)
mock_api.get_forecast.side_effect = lambda loc_id, horizon=3: make_forecast(loc_id)
mock_api.get_historical.side_effect = lambda loc_id: make_historical(loc_id)
mock_api.get_scenarios.return_value = [
    {"id": "temp_plus_2", "name": "Temperature +2C", "description": "Test"},
]
mock_api.simulate_scenario.return_value = {
    "status": "success",
    "data": {"location_id": "KA-BLR-001", "rainfall": 25.0, "max_temp": 34.0},
}
mock_api.run_monte_carlo.return_value = {
    "n_samples": 100,
    "summary": {"temp": {"mean": 1.5}},
    "confidence_intervals": {"temp": {"mean": 1.5, "lower": 1.0, "upper": 2.0, "std": 0.25}},
}
mock_api.compare_scenarios.return_value = {
    "total_comparisons": 1,
    "comparisons": [
        {"scenario_a": "A", "scenario_b": "B", "summary": "...", "variable_deltas": {}}
    ],
}
mock_api.run_ensemble.return_value = {
    "n_members": 5,
    "summary": {
        "temp": {
            "ensemble_mean": 1.5,
            "ensemble_std": 0.25,
            "ensemble_p5": 1.0,
            "ensemble_p95": 2.0,
        }
    },
    "ensemble_mean": {"temp": [1.5, 1.6]},
}
mock_api.get_risk.side_effect = lambda loc_id: {
    "location_id": loc_id,
    "composite_risk": 25.0,
    "heat_risk": 32.0,
    "flood_risk": 18.0,
    "drought_risk": 14.0,
    "shap_summary": {"Rainfall": 0.02, "MaxTemp": 0.03},
}
mock_api.get_risk_list.return_value = [
    {
        "district": "Bengaluru Urban",
        "composite_risk": 25.0,
        "heat_risk": 10.0,
        "flood_risk": 5.0,
        "drought_risk": 5.0,
    },
]
mock_api.get_district_summary.return_value = {
    "risk_level": "Moderate",
    "district": "Bengaluru Urban",
    "total_rainfall_ytd": 500.0,
    "avg_max_temp": 30.0,
    "avg_min_temp": 20.0,
}

# Patch create_api_client to return mock
dashboard.services.api_client.create_api_client = lambda: mock_api

PAGES = [
    "app",
    "01_climate_overview",
    "02_forecast_viewer",
    "03_twin_state",
    "04_scenario_simulator",
    "05_climate_risk",
    "06_reports",
    "07_copilot_chat",
    "08_knowledge_base",
    "09_feedback",
    "10_twin_state_bhai",
]


def diagnose_page(page_name: str) -> dict:
    """Run app.py targeting the given page."""
    import streamlit as st

    result = {
        "page": page_name,
        "importerror": False,
        "import_exception": None,
        "render_exception": None,
        "render_exception_type": None,
        "render_exception_traceback": None,
        "markers_found": [],
        "errors_found": [],
        "log": [],
    }

    class LogCaptureHandler(logging.Handler):
        def emit(self, record):
            line = self.format(record)
            result["log"].append(line)

    log_capture = LogCaptureHandler()
    log_capture.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
    logging.getLogger("__main__").addHandler(log_capture)
    logging.getLogger("dashboard").addHandler(log_capture)

    try:
        from streamlit.testing.v1.app_test import AppTest

        at = AppTest.from_file("dashboard/app.py", default_timeout=5)

        # If not app page, we need to navigate after first run
        if page_name != "app":
            # First run to get the selectbox initialized
            at.run()
            # Find the selectbox and change it
            pages_config = None
            import importlib

            cfg = importlib.import_module("dashboard.config.config")
            pages_config = cfg.PAGES

            # Map page file -> title
            page_to_title = {p["file"]: p["title"] for p in pages_config}
            if page_name in page_to_title:
                target_title = page_to_title[page_name]
                # Navigate using the selectbox
                at.selectbox(key="nav_select").set_value(target_title).run()
        else:
            at.run()

        # Collect results
        for w in at:
            wt = type(w).__name__
            if wt == "Exception":
                result["errors_found"].append(str(w))
            elif wt == "Warning":
                pass

        # Check for text content
        all_text = []
        for w in at:
            if hasattr(w, "value") and isinstance(w.value, str):
                all_text.append(w.value)
            elif hasattr(w, "title"):
                all_text.append(str(w.title))
            elif hasattr(w, "data") and isinstance(w.data, str):
                all_text.append(w.data)

        combined = " ".join(all_text)

        # Check for debug markers
        import re

        markers = re.findall(r"\d+_[a-z_]+ render\(\) ENTERED", combined)
        result["markers_found"] = markers

        # Check for error messages
        if "RENDER FAILED" in combined or "Failed to import" in combined:
            result["render_exception"] = "Found error message in output"

        # Check for "render() COMPLETED OK" in logs
        for line in result["log"]:
            if "render() COMPLETED OK" in line:
                result["log"].append("*** render() COMPLETED OK ***")
                break

    except Exception as e:
        import traceback

        result["render_exception"] = str(e)
        result["render_exception_type"] = type(e).__name__
        result["render_exception_traceback"] = traceback.format_exc()

    finally:
        logging.getLogger("__main__").removeHandler(log_capture)
        logging.getLogger("dashboard").removeHandler(log_capture)

    return result


if __name__ == "__main__":
    logger.info("=== Diagnosis v2 starting ===")

    for page_name in PAGES:
        logger.info("--- Diagnosing page: %s ---", page_name)
        diag = diagnose_page(page_name)

        print(f"\n{'=' * 70}")
        print(f"  PAGE: {page_name}")
        print(f"{'=' * 70}")

        if diag["import_exception"]:
            print(f"  Import error: {diag['import_exception']}")
        else:
            print(f"  Module imported: YES")

        if diag["markers_found"]:
            for m in diag["markers_found"]:
                print(f"  Debug marker: YES — '{m}'")
        else:
            print(f"  Debug marker: NO")

        if diag["render_exception"]:
            print(
                f"  render() exception: {diag['render_exception_type']}: {diag['render_exception']}"
            )
            if diag["render_exception_traceback"]:
                for line in diag["render_exception_traceback"].splitlines():
                    print(f"    {line}")
        else:
            print(f"  render() exception: NONE")

        # Check for completion
        completed = any("render() COMPLETED OK" in l for l in diag["log"])
        print(f"  render() completed: {'YES' if completed else 'NO'}")

        if diag["errors_found"]:
            print(f"  Streamlit errors: {len(diag['errors_found'])}")
            for e in diag["errors_found"][:3]:
                print(f"    - {e}")

        # Show relevant log lines
        print(f"  Key log lines ({len(diag['log'])} total):")
        for line in diag["log"]:
            if "=== " in line:
                print(f"    {line}")
            elif "WARNING" in line and "unavailable" in line:
                pass  # skip API unavailable warnings (expected)
            elif "Uvicorn" in line:
                pass  # skip server messages
            elif "missing ScriptRunContext" in line:
                pass
            else:
                print(f"    {line}")
