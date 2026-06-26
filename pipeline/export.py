"""Module 5: Dataset Export.

Splits final data into training (70%), validation (15%), and testing (15%).
Exports as CSV files to data/processed/ with the expected column set.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

EXPECTED_OUTPUT_COLUMNS: list[str] = [
    "Date",
    "Latitude",
    "Longitude",
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


def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and reorder columns to match the expected output schema."""
    available = [c for c in EXPECTED_OUTPUT_COLUMNS if c in df.columns]
    missing = [c for c in EXPECTED_OUTPUT_COLUMNS if c not in df.columns]
    if missing:
        logger.warning("Missing expected output columns: %s", missing)
    return df[available].copy()


def temporal_train_val_test_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split data chronologically to prevent data leakage.

    Sorts by date, then splits 70/15/15 along the time axis.
    """
    total = len(df)
    if total == 0:
        logger.warning("Empty DataFrame, returning empty splits")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df.sort_values("Date").reset_index(drop=True)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()
    logger.info(
        "Split complete: train=%d (%.1f%%), val=%d (%.1f%%), test=%d (%.1f%%)",
        len(train_df),
        100 * len(train_df) / total,
        len(val_df),
        100 * len(val_df) / total,
        len(test_df),
        100 * len(test_df) / total,
    )
    return train_df, val_df, test_df


def save_split(
    df: pd.DataFrame,
    output_dir: Path,
    filename: str,
) -> Path:
    """Save a split DataFrame as CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename
    df.to_csv(filepath, index=False)
    logger.info("Saved %s: %d rows, %d columns", filename, len(df), len(df.columns))
    return filepath


def export_datasets(
    df: pd.DataFrame,
    config: dict[str, Any],
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Export train/val/test splits as CSV files.

    Returns dict mapping split name to file path.
    """
    if output_dir is None:
        output_dir = Path(config["data"]["processed_dir"])
    train_ratio = config["pipeline"]["train_split"]
    val_ratio = config["pipeline"]["val_split"]
    df_out = select_output_columns(df)
    train_df, val_df, test_df = temporal_train_val_test_split(
        df_out, train_ratio, val_ratio
    )
    results = {}
    results["training"] = save_split(train_df, output_dir, "training.csv")
    results["validation"] = save_split(val_df, output_dir, "validation.csv")
    results["testing"] = save_split(test_df, output_dir, "testing.csv")
    return results
