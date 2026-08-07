"""Module 4: Feature Engineering.

Generates all required features from cleaned climate data:
Day of Year, Month, Week, Season, Monsoon Indicator,
Previous 7-Day Rainfall, Previous 30-Day Rainfall,
Rolling Mean, Rolling Std Dev, Temperature Difference, Rainfall Trend.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

SEASON_MAP: dict[int, str] = {
    1: "Winter",
    2: "Winter",
    3: "Summer",
    4: "Summer",
    5: "Summer",
    6: "Monsoon",
    7: "Monsoon",
    8: "Monsoon",
    9: "Monsoon",
    10: "Post-Monsoon",
    11: "Post-Monsoon",
    12: "Winter",
}

MONSOON_MONTHS: list[int] = [6, 7, 8, 9]


def load_config(config_path: str = "config/data_config.yaml") -> dict[str, Any]:
    """Load pipeline configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add date-based features: day of year, month, week, season, monsoon indicator."""
    dates = pd.to_datetime(df["Date"])
    df["DayOfYear"] = dates.dt.dayofyear
    df["Month"] = dates.dt.month
    df["Week"] = dates.dt.isocalendar().week.astype(int)
    df["Season"] = df["Month"].map(SEASON_MAP)
    df["Monsoon"] = df["Month"].isin(MONSOON_MONTHS).astype(int)
    logger.info("Added temporal features: DayOfYear, Month, Week, Season, Monsoon")
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling window features for rainfall and temperature."""
    df = df.sort_values(["Latitude", "Longitude", "Date"]).reset_index(drop=True)
    group_cols = ["Latitude", "Longitude"]
    if "Rainfall" in df.columns:
        df["RollingRain7"] = df.groupby(group_cols)["Rainfall"].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )
        df["RollingRain30"] = df.groupby(group_cols)["Rainfall"].transform(
            lambda x: x.rolling(30, min_periods=1).mean()
        )
        df["RainfallTrend"] = df.groupby(group_cols)["Rainfall"].transform(
            lambda x: x.rolling(30, min_periods=1).apply(
                lambda y: np.polyfit(range(len(y)), y, 1)[0] if len(y) >= 2 else 0.0
            )
        )
    if "MaxTemp" in df.columns:
        df["RollingTemp7"] = df.groupby(group_cols)["MaxTemp"].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )
        df["RollingTemp30"] = df.groupby(group_cols)["MaxTemp"].transform(
            lambda x: x.rolling(30, min_periods=1).mean()
        )
    if "MaxTemp" in df.columns and "MinTemp" in df.columns:
        df["TempDiff"] = df["MaxTemp"] - df["MinTemp"]
    logger.info(
        "Added rolling features: RollingRain7, RollingRain30, RollingTemp7, RollingTemp30, RainfallTrend, TempDiff"
    )
    return df


def add_prior_rainfall(df: pd.DataFrame) -> pd.DataFrame:
    """Add prior rainfall accumulation features (prev 7-day and 30-day sum)."""
    df = df.sort_values(["Latitude", "Longitude", "Date"]).reset_index(drop=True)
    group_cols = ["Latitude", "Longitude"]
    if "Rainfall" in df.columns:
        df["PriorRain7"] = df.groupby(group_cols)["Rainfall"].transform(
            lambda x: x.shift(1).rolling(7, min_periods=1).sum()
        )
        df["PriorRain30"] = df.groupby(group_cols)["Rainfall"].transform(
            lambda x: x.shift(1).rolling(30, min_periods=1).sum()
        )
        df["PriorRain7"] = df["PriorRain7"].fillna(0.0)
        df["PriorRain30"] = df["PriorRain30"].fillna(0.0)
    logger.info("Added prior rainfall features: PriorRain7, PriorRain30")
    return df


def round_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Round numeric feature columns to 2 decimal places."""
    float_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    skip_cols = {"Month", "Week", "DayOfYear", "Monsoon"}
    for col in float_cols:
        if col not in skip_cols and col not in ("Latitude", "Longitude"):
            df[col] = df[col].round(2)
    return df


def engineer_features(df: pd.DataFrame, output_path: Path | None = None) -> pd.DataFrame:
    """Run the full feature engineering pipeline on cleaned data."""
    df = add_temporal_features(df)
    df = add_rolling_features(df)
    df = add_prior_rainfall(df)
    df = round_feature_columns(df)
    logger.info("Feature engineering complete: %d rows, %d columns", len(df), len(df.columns))
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        logger.info("Features saved to %s", output_path)
    return df
