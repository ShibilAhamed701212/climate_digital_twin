"""Unit test conftest — skip torch-dependent test files if torch unavailable.

Each file already has its own module-level try/except+pytest.skip guard.
We only exclude them pre-collection when torch is genuinely unavailable.
"""

torch_ok = False
try:
    import torch  # noqa: F401

    torch_ok = True
except Exception:
    torch_ok = False

if not torch_ok:
    collect_ignore = [
        "test_data_loader.py",
        "test_trainer.py",
        "test_predictor.py",
        "test_physics.py",
        "test_models.py",
        "test_evaluator.py",
        "test_all_models.py",
        "test_tuning_optimizer.py",
    ]
