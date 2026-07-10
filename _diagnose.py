"""Diagnostic: Run each page's render() and collect logs + exceptions."""

import logging
import sys
import time
import traceback
from unittest.mock import MagicMock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger("diagnose")

PAGES = [
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

# We'll use AppTest from Streamlit to simulate each page's render()
from streamlit.testing.v1.app_test import AppTest


def diagnose_page(page_name: str) -> dict:
    """Run app.py and navigate to the given page, return diagnostics."""
    result = {
        "page": page_name,
        "imported": False,
        "render_entered": False,
        "debug_marker_visible": False,
        "last_log_line": "",
        "exception": None,
        "exception_type": None,
        "exception_traceback": None,
        "executed_statements": [],
        "errors": [],
        "warnings": [],
    }

    try:
        # Set up the page selection before running
        from streamlit.testing.v1.app_test import AppTest

        at = AppTest.from_file("dashboard/app.py", default_timeout=10)

        # Run the app once with default (app page)
        at.run()

        # Collect all error messages from the run
        if at.errors:
            for err in at.errors:
                result["errors"].append(str(err))

        # Some pages have exception output as st.error
        for widget in at:
            widget_type = type(widget).__name__
            widget_value = ""
            if hasattr(widget, "value"):
                widget_value = str(widget.value)
            elif hasattr(widget, "title"):
                widget_value = widget.title
            elif hasattr(widget, "data"):
                widget_value = str(widget.data)[:100]
            result["executed_statements"].append(f"{widget_type}: {widget_value[:80]}")

    except Exception as e:
        result["exception"] = str(e)
        result["exception_type"] = type(e).__name__
        result["exception_traceback"] = traceback.format_exc()

    return result


if __name__ == "__main__":
    logger.info("=== Starting Diagnosis ===")

    for page_name in PAGES:
        logger.info("--- Diagnosing page: %s ---", page_name)
        diag = diagnose_page(page_name)

        print(f"\n{'=' * 60}")
        print(f"PAGE: {page_name}")
        print(f"{'=' * 60}")
        print(f"  Imported:              {'YES' if diag['imported'] else 'NO'}")
        print(f"  render() entered:      {'YES' if diag['render_entered'] else 'NO'}")
        print(f"  Debug marker visible:  {'YES' if diag['debug_marker_visible'] else 'NO'}")

        if diag["exception"]:
            print(f"  Exception:             {diag['exception_type']}: {diag['exception']}")
            print(f"  Traceback:")
            for line in (diag["exception_traceback"] or "").splitlines():
                print(f"    {line}")

        if diag["last_log_line"]:
            print(f"  Last log line:         {diag['last_log_line']}")

        if diag["errors"]:
            print(f"  Errors ({len(diag['errors'])}):")
            for err in diag["errors"]:
                print(f"    - {err}")

        print("  Executed statements:")
        for stmt in diag["executed_statements"][:20]:
            print(f"    {stmt}")
        if len(diag["executed_statements"]) > 20:
            print(f"    ... and {len(diag['executed_statements']) - 20} more")
