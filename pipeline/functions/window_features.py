"""Window-based feature computation functions for the data pipeline.

Pure functions for computing lag, rolling, and seasonal features
that can be called by the pipeline or FeatureEngine.
"""


import numpy as np
import pandas as pd


def compute_lag_features(
    df: pd.DataFrame,
    column: str,
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """Compute lagged versions of a column.

    Args:
        df: Input DataFrame.
        column: Column name to lag.
        lags: Lag periods (default: [1, 7, 30]).

    Returns:
        DataFrame with added lag columns named '{column}_lag_{lag}'.
    """
    if lags is None:
        lags = [1, 7, 30]
    result = df.copy()
    for lag in lags:
        result[f"{column}_lag_{lag}"] = result[column].shift(lag)
    return result


def compute_rolling_features(
    df: pd.DataFrame,
    column: str,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Compute rolling window statistics for a column.

    Generates rolling mean and standard deviation for each window size.

    Args:
        df: Input DataFrame.
        column: Column name to compute rolling stats for.
        windows: Window sizes (default: [7, 30, 90]).

    Returns:
        DataFrame with added rolling feature columns.
    """
    if windows is None:
        windows = [7, 30, 90]
    result = df.copy()
    for window in windows:
        result[f"{column}_rolling_mean_{window}"] = (
            result[column].rolling(window=window, min_periods=1).mean()
        )
        result[f"{column}_rolling_std_{window}"] = (
            result[column].rolling(window=window, min_periods=1).std()
        )
    return result


def compute_seasonal_features(
    df: pd.DataFrame,
    date_column: str,
) -> pd.DataFrame:
    """Compute seasonal calendar features from a date column.

    Generates: year, month, day, day_of_year, day_of_week, quarter,
    is_weekend, season.

    Args:
        df: Input DataFrame.
        date_column: Name of the datetime column.

    Returns:
        DataFrame with added seasonal feature columns.
    """
    result = df.copy()
    dates = pd.to_datetime(result[date_column])

    result["year"] = dates.dt.year.astype(np.int32)
    result["month"] = dates.dt.month.astype(np.int32)
    result["day"] = dates.dt.day.astype(np.int32)
    result["day_of_year"] = dates.dt.dayofyear.astype(np.int32)
    result["day_of_week"] = dates.dt.dayofweek.astype(np.int32)
    result["quarter"] = dates.dt.quarter.astype(np.int32)
    result["is_weekend"] = (dates.dt.dayofweek >= 5).astype(np.int32)

    season_map: dict[int, str] = {
        1: "winter",
        2: "winter",
        3: "spring",
        4: "spring",
        5: "spring",
        6: "summer",
        7: "summer",
        8: "summer",
        9: "autumn",
        10: "autumn",
        11: "autumn",
        12: "winter",
    }
    result["season"] = dates.dt.month.map(season_map)

    return result


def compute_all_window_features(
    df: pd.DataFrame,
    date_column: str,
    numeric_columns: list[str] | None = None,
    lags: list[int] | None = None,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Convenience function: compute lag + rolling + seasonal features.

    Args:
        df: Input DataFrame.
        date_column: Name of the datetime column.
        numeric_columns: List of numeric columns to compute lags/rolling for.
            If None, uses all numeric columns.
        lags: Lag periods (default: [1, 7, 30]).
        windows: Rolling window sizes (default: [7, 30, 90]).

    Returns:
        DataFrame with all window features added.
    """
    if numeric_columns is None:
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        if date_column in df.columns:
            numeric_columns = [c for c in numeric_columns if c != date_column]

    result = compute_seasonal_features(df, date_column)

    for col in numeric_columns:
        if col in result.columns:
            result = compute_lag_features(result, col, lags)
            result = compute_rolling_features(result, col, windows)

    return result
