"""Regression tests for scripts/seed_forecast_data.py."""

from scripts.seed_forecast_data import FEATURE_COLUMNS, generate


def test_generate_returns_all_feature_columns_in_order() -> None:
    df = generate(n_samples=20, seq_len=5)

    assert list(df.columns) == FEATURE_COLUMNS
    assert len(df) == 25
    assert not df.isna().any().any()


def test_generate_respects_min_below_max_temperature() -> None:
    df = generate(n_samples=50, seq_len=0)

    assert (df["MinTemp"] <= df["MaxTemp"] - 2 + 1e-9).all()
