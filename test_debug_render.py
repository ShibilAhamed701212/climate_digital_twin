"""Debug: test each page module's render function for errors."""

import importlib
import sys
import traceback

from dashboard.config.config import PAGES
from dashboard.services.api_client import create_api_client

api = create_api_client()
filters = {
    "district": "All",
    "location_id": "KA-BLR-001",
    "variable": "Rainfall",
    "horizon": 3,
}

for page in PAGES:
    title = page["title"]
    file = page["file"]
    module_name = f"dashboard.page_views.{file}"

    print(f"\n{'=' * 60}")
    print(f"Testing: {title} ({module_name})")
    print(f"{'=' * 60}")

    try:
        # Force reimport
        if module_name in sys.modules:
            del sys.modules[module_name]

        mod = importlib.import_module(module_name)
        print(f"  ✓ Module imported successfully")

        # Check for render function
        if not hasattr(mod, "render"):
            print(f"  ✗ NO RENDER FUNCTION FOUND")
            continue

        render_fn = mod.render
        print(f"  ✓ render() exists: {render_fn}")

        # Test the signature
        import inspect

        sig = inspect.signature(render_fn)
        print(f"  ✓ Signature: {sig}")

        # Now actually call the render function
        # Note: this will fail because there's no Streamlit context
        print(f"  → Attempting to call render()...")
        try:
            render_fn(api, filters)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"  ✗ render() raised: {type(e).__name__}: {e}")
            # Check if it's Streamlit-related (expected outside Streamlit)
            if "NoSessionContext" in str(e) or "session" in str(e).lower():
                print(f"    (Expected — no Streamlit session in test context)")
            else:
                print(f"    Traceback (first 20 lines):")
                for line in tb.split("\n")[:20]:
                    print(f"      {line}")

        print(f"  ✓ Module inspection complete")

    except Exception as e:
        tb = traceback.format_exc()
        print(f"  ✗ FAILED: {type(e).__name__}: {e}")
        for line in tb.split("\n")[-10:]:
            print(f"    {line}")

print(f"\n{'=' * 60}")
print("Diagnostic complete")
print(f"{'=' * 60}")
