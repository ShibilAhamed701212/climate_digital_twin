"""Integration test conftest — skip torch-dependent test files if unavailable."""

torch_ok = False
try:
    import torch  # noqa: F401

    torch_ok = True
except Exception:
    torch_ok = False

if not torch_ok:
    collect_ignore = [
        "test_forecast.py",
    ]
