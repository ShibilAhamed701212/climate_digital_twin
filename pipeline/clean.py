"""Module 3: Data Cleaning.

Removes duplicates, handles missing values, corrects invalid coordinates,
normalizes date formats, and standardizes units. Outputs go to data/interim/.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/data_config.yaml") -> dict[str, Any]:
    """Load pipeline configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def remove_duplicates(df: pd.DataFrame, subset: list | None = None) -> pd.DataFrame:
    """Remove duplicate rows, keeping the first occurrence."""
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep="first")
    after = len(df)
    if before > after:
        logger.info("Removed %d duplicate rows", before - after)
    return df


def handle_missing_values(df: pd.DataFrame, method: str = "interpolate") -> pd.DataFrame:
    """Handle missing values using interpolation or forward fill.

    For numeric columns: linear interpolation (time-aware if Date is present).
    For categorical columns: forward fill then backward fill.
    """
    before = df.isnull().sum().sum()
    if before == 0:
        return df
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if "Date" in df.columns and method == "interpolate":
        df = df.sort_values("Date").reset_index(drop=True)
    for col in numeric_cols:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            df[col] = df[col].interpolate(method="linear", limit_direction="both")
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    for col in cat_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].ffill().bfill()
    after = df.isnull().sum().sum()
    logger.info(
        "Missing values handled: %d before -> %d after (filled %d)",
        before,
        after,
        before - after,
    )
    return df


def clip_outliers(
    df: pd.DataFrame, column: str, lower_percentile: float = 0.01, upper_percentile: float = 0.99
) -> pd.DataFrame:
    """Clip extreme outliers in a numeric column."""
    if column not in df.columns:
        return df
    lower = df[column].quantile(lower_percentile)
    upper = df[column].quantile(upper_percentile)
    clipped_before = ((df[column] < lower) | (df[column] > upper)).sum()
    df[column] = df[column].clip(lower, upper)
    logger.info(
        "Clipped %d outliers in %s to [%.2f, %.2f]",
        clipped_before,
        column,
        lower,
        upper,
    )
    return df


def correct_coordinates(df: pd.DataFrame, bounds: dict[str, float]) -> pd.DataFrame:
    """Remove records with coordinates outside the valid bounds."""
    before = len(df)
    mask_lat = (df["Latitude"] >= bounds["min_lat"]) & (df["Latitude"] <= bounds["max_lat"])
    mask_lon = (df["Longitude"] >= bounds["min_lon"]) & (df["Longitude"] <= bounds["max_lon"])
    df = df[mask_lat & mask_lon].reset_index(drop=True)
    after = len(df)
    if before > after:
        logger.info("Removed %d records outside coordinate bounds", before - after)
    return df


def normalize_date_format(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure Date column is datetime and normalized."""
    if "Date" not in df.columns:
        return df
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    invalid_dates = df["Date"].isnull().sum()
    if invalid_dates > 0:
        logger.warning("Found %d invalid dates, dropping those records", invalid_dates)
        df = df.dropna(subset=["Date"])
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def standardize_units(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize units: rainfall in mm, temperature in Celsius."""
    if "Rainfall" in df.columns:
        df["Rainfall"] = pd.to_numeric(df["Rainfall"], errors="coerce")
        df.loc[df["Rainfall"] < 0, "Rainfall"] = 0.0
    if "MaxTemp" in df.columns:
        df["MaxTemp"] = pd.to_numeric(df["MaxTemp"], errors="coerce")
    if "MinTemp" in df.columns:
        df["MinTemp"] = pd.to_numeric(df["MinTemp"], errors="coerce")
    return df


def merge_datasets(
    rainfall_df: pd.DataFrame,
    max_temp_df: pd.DataFrame,
    min_temp_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge rainfall and temperature datasets on Date, Latitude, Longitude."""
    df = rainfall_df.merge(max_temp_df, on=["Date", "Latitude", "Longitude"], how="outer")
    df = df.merge(min_temp_df, on=["Date", "Latitude", "Longitude"], how="outer")
    df = df.sort_values(["Date", "Latitude", "Longitude"]).reset_index(drop=True)
    logger.info("Merged dataset: %d rows, %d columns", len(df), len(df.columns))
    return df


def clean_dataset(
    df: pd.DataFrame,
    bounds: dict[str, float],
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Run the full cleaning pipeline on a merged dataset."""
    df = remove_duplicates(df)
    df = normalize_date_format(df)
    df = standardize_units(df)
    df = correct_coordinates(df, bounds)
    df = clip_outliers(df, "Rainfall", 0.01, 0.99)
    df = clip_outliers(df, "MaxTemp", 0.001, 0.999)
    df = clip_outliers(df, "MinTemp", 0.001, 0.999)
    df = handle_missing_values(df)
    logger.info("Cleaning complete: %d rows, %d columns", len(df), len(df.columns))
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        logger.info("Cleaned data saved to %s", output_path)
    return df
