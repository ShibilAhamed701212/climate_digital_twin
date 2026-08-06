"""Phase 13 — Forecast Model Benchmark.

Benchmarks all feasible NeuralForecast models against persistence,
climatology, and the existing LSTM baseline on REAL data.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from neuralforecast import NeuralForecast
from neuralforecast.models import NHITS, NBEATS
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BENCHMARK_DIR = Path("data/benchmarks")
BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)


def load_training_data() -> pd.DataFrame:
    """Load and merge all available REAL training data."""
    train = pd.read_csv("data/real/training.csv", parse_dates=["Date"])
    val = pd.read_csv("data/real/validation.csv", parse_dates=["Date"])
    test = pd.read_csv("data/real/testing.csv", parse_dates=["Date"])
    df = pd.concat([train, val, test]).sort_values("Date").reset_index(drop=True)
    # Add time features
    df["Month"] = df["Date"].dt.month
    df["Week"] = df["Date"].dt.isocalendar().week.astype(float)
    df["Season"] = df["Month"].apply(lambda m: 1 if m in (6, 7, 8, 9) else 0)
    df["Monsoon"] = df["Season"]
    # NeuralForecast expects 'ds' (timestamp), 'y' (target), and 'unique_id'
    df["ds"] = df["Date"]
    df["unique_id"] = "bengaluru"
    return df


def prepare_nf_format(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """Convert to NeuralForecast format: ds, y, unique_id."""
    return df[["ds", target, "unique_id"]].rename(columns={target: "y"})


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
        "bias": float(np.mean(y_pred - y_true)),
        "smape": float(
            200 * np.mean(np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred) + 1e-8))
        ),
    }


def benchmark_persistence(df: pd.DataFrame, horizon: int = 1) -> dict[str, dict]:
    """Persistence: predict tomorrow = today."""
    results = {}
    test_end = int(len(df) * 0.85)
    test_df = df.iloc[test_end:]
    for target, col in [("tmax", "MaxTemp"), ("tmin", "MinTemp"), ("rainfall", "Rainfall")]:
        y_true = test_df[col].values[horizon:]
        y_pred = test_df[col].values[:-horizon]
        results[target] = compute_metrics(y_true, y_pred)
    return results


def benchmark_climatology(df: pd.DataFrame) -> dict[str, dict]:
    """Climatology: predict monthly mean from training."""
    results = {}
    train_end = int(len(df) * 0.70)
    train_df = df.iloc[:train_end]
    test_df = df.iloc[int(len(df) * 0.85) :]
    monthly_means = train_df.groupby("Month")[["MaxTemp", "MinTemp", "Rainfall"]].mean()
    for target, col in [("tmax", "MaxTemp"), ("tmin", "MinTemp"), ("rainfall", "Rainfall")]:
        y_pred = np.array([monthly_means.loc[m, col] for m in test_df["Month"]])
        y_true = test_df[col].values
        results[target] = compute_metrics(y_true, y_pred)
    return results


def benchmark_neuralforecast(
    df: pd.DataFrame, model_name: str, model_cls, model_kwargs: dict
) -> dict:
    """Benchmark a single NeuralForecast model."""
    results = {}
    for target, col in [("tmax", "MaxTemp"), ("tmin", "MinTemp"), ("rainfall", "Rainfall")]:
        y_df = prepare_nf_format(df, col)

        # Split: train 70%, val 15%, test 15%
        n = len(y_df)
        train_n = int(n * 0.70)
        val_n = int(n * 0.85)
        train_df = y_df.iloc[:val_n]  # NF trains on train+val, we evaluate on test
        test_df = y_df.iloc[val_n:]

        print(f"    {target}: training {model_name} on {len(train_df)} samples...", end=" ")

        try:
            model = model_cls(
                h=1,  # 1-step ahead
                input_size=30,  # 30-day lookback
                max_steps=100,  # limited for benchmark speed
                **model_kwargs,
            )
            nf = NeuralForecast(models=[model], freq="D")
            start = time.time()
            nf.fit(df=train_df)
            train_time = time.time() - start

            start = time.time()
            fcst = nf.predict()
            infer_time = time.time() - start

            # Merge predictions with test
            merged = fcst.merge(test_df[["ds", "y"]], on="ds", how="inner")
            if len(merged) > 5:
                metrics = compute_metrics(merged["y"].values, merged[model_name].values)
                metrics["train_time_s"] = round(train_time, 1)
                metrics["infer_time_s"] = round(infer_time, 3)
                metrics["samples"] = len(merged)
                results[target] = metrics
                print(f"RMSE={metrics['rmse']:.3f} R2={metrics['r2']:.3f}")
            else:
                print("too few predictions")
        except Exception as e:
            print(f"FAILED: {e}")

    return results


def run_benchmarks():
    """Run full benchmark suite."""
    print("=" * 60)
    print("PHASE 13 — FORECAST MODEL BENCHMARK")
    print("=" * 60)

    df = load_training_data()
    print(f"Dataset: {len(df)} samples, {df.ds.min().date()} to {df.ds.max().date()}")
    print(
        f"GPU: {torch.cuda.get_device_name(0)}, VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB"
    )
    print()

    all_results = {}
    device_kwargs = {"accelerator": "gpu", "devices": 1} if torch.cuda.is_available() else {}

    # Baselines
    print("[PERSISTENCE]")
    all_results["persistence"] = benchmark_persistence(df)
    print(
        f"  Tmax: RMSE={all_results['persistence']['tmax']['rmse']:.3f} "
        f"Tmin: {all_results['persistence']['tmin']['rmse']:.3f} "
        f"Rain: {all_results['persistence']['rainfall']['rmse']:.3f}"
    )

    print("[CLIMATOLOGY]")
    all_results["climatology"] = benchmark_climatology(df)
    print(
        f"  Tmax: RMSE={all_results['climatology']['tmax']['rmse']:.3f} "
        f"Rain: {all_results['climatology']['rainfall']['rmse']:.3f}"
    )

    # NeuralForecast models
    models_to_bench = [
        (
            "NHITS",
            NHITS,
            {
                "n_pool_kernel_size": [2, 2, 1],
                "n_freq_downsample": [2, 1, 1],
                "mlp_units": [[64, 64], [64, 64], [64, 64]],
            },
        ),
        ("NBEATS", NBEATS, {"mlp_units": [[64, 64], [64, 64]]}),
    ]

    for name, cls, kwargs in models_to_bench:
        print(f"\n[{name}]")
        try:
            results = benchmark_neuralforecast(df, name, cls, {**kwargs, **device_kwargs})
            all_results[name] = results
        except Exception as e:
            print(f"  SKIPPED: {e}")

    # Save results
    output_path = BENCHMARK_DIR / "phase13_benchmark.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")

    # Print leaderboard
    print("\n=== LEADERBOARD (Tmax RMSE) ===")
    leaderboard = []
    for name, res in all_results.items():
        if "tmax" in res:
            leaderboard.append((name, res["tmax"]["rmse"]))
    leaderboard.sort(key=lambda x: x[1])
    for rank, (name, rmse) in enumerate(leaderboard, 1):
        print(f"  {rank}. {name}: {rmse:.4f}")

    return all_results


if __name__ == "__main__":
    run_benchmarks()
