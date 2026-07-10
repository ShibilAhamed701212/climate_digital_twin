#!/usr/bin/env python3
"""Generate processed climate data CSV files for the forecast engine."""

import os

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "Rainfall",
    "MaxTemp",
    "MinTemp",
    "Month",
    "Week",
    "Season",
    "Monsoon",
    "RollingRain7",
    "RollingRain30",
    "RollingTemp7",
    "RollingTemp30",
]


def _season(month: int) -> int:
    if month in (1, 2):
        return 0
    if 3 <= month <= 5:
        return 1
    if 6 <= month <= 9:
        return 2
    return 3


def _is_monsoon(month: int) -> int:
    return 1 if 6 <= month <= 9 else 0


def generate(n_samples: int, seq_len: int = 30) -> pd.DataFrame:
    """Generate a realistic climate dataset for Karnataka with seasonal patterns."""
    rows = n_samples + seq_len
    data = {col: [] for col in FEATURE_COLUMNS}

    rng = np.random.default_rng(42)

    for i in range(rows):
        dt = pd.Timestamp("2023-01-01") + pd.DateOffset(days=i)
        month = dt.month
        week = dt.isocalendar().week

        # Rainfall with seasonal patterns
        if month in (6, 7, 8, 9):
            rainfall = max(0, rng.normal(180, 80))
        elif month in (10, 11):
            rainfall = max(0, rng.normal(80, 40))
        elif month in (1, 2):
            rainfall = max(0, rng.normal(10, 8))
        else:
            rainfall = max(0, rng.normal(40, 25))

        # Temperature with seasonal patterns
        if month in (3, 4, 5):
            max_t = rng.normal(34, 3)
            min_t = rng.normal(22, 2)
        elif month in (6, 7, 8, 9):
            max_t = rng.normal(28, 2)
            min_t = rng.normal(22, 1.5)
        elif month in (10, 11):
            max_t = rng.normal(30, 2)
            min_t = rng.normal(20, 2)
        else:
            max_t = rng.normal(28, 3)
            min_t = rng.normal(17, 2)

        min_t = min(min_t, max_t - 2)  # physical constraint

        data["Rainfall"].append(round(float(rainfall), 2))
        data["MaxTemp"].append(round(float(max_t), 2))
        data["MinTemp"].append(round(float(min_t), 2))
        data["Month"].append(float(month))
        data["Week"].append(float(week))
        data["Season"].append(float(_season(month)))
        data["Monsoon"].append(float(_is_monsoon(month)))

    df = pd.DataFrame(data)

    # Compute rolling features
    df["RollingRain7"] = df["Rainfall"].rolling(window=7, min_periods=1).mean().round(2)
    df["RollingRain30"] = df["Rainfall"].rolling(window=30, min_periods=1).mean().round(2)
    df["RollingTemp7"] = df["MaxTemp"].rolling(window=7, min_periods=1).mean().round(2)
    df["RollingTemp30"] = df["MaxTemp"].rolling(window=30, min_periods=1).mean().round(2)

    return df


def main():
    output_dir = "data/processed"
    os.makedirs(output_dir, exist_ok=True)

    datasets = {
        "training.csv": 5000,
        "validation.csv": 1000,
        "testing.csv": 500,
    }

    for filename, n_samples in datasets.items():
        df = generate(n_samples)
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False)
        print(f"Created {filepath}: {len(df)} rows x {len(df.columns)} cols")

    # Verify
    verify = pd.read_csv(os.path.join(output_dir, "testing.csv"))
    print(f"Columns: {list(verify.columns)}")
    print(f"Sample:\n{verify.head(2).to_string()}")


if __name__ == "__main__":
    main()
