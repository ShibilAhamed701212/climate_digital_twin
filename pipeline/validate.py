"""Module 2: Dataset Validator.

Verifies file formats, checks missing files, validates date ranges,
verifies expected columns, and detects corrupt records.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/data_config.yaml") -> dict[str, Any]:
    """Load pipeline configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def validate_file_exists(filepath: Path) -> bool:
    """Check that a file exists and has non-zero size."""
    if not filepath.exists():
        logger.error("File not found: %s", filepath)
        return False
    if filepath.stat().st_size == 0:
        logger.error("File is empty: %s", filepath)
        return False
    return True


def validate_columns(
    df: pd.DataFrame, expected_columns: list[str], label: str
) -> list[str]:
    """Verify that expected columns exist in the DataFrame."""
    missing = [c for c in expected_columns if c not in df.columns]
    if missing:
        logger.error("%s missing columns: %s", label, missing)
    return missing


def validate_date_range(
    df: pd.DataFrame, start_date: str, end_date: str, label: str
) -> bool:
    """Validate that all dates fall within the expected range."""
    if "Date" not in df.columns:
        logger.error("%s has no Date column", label)
        return False
    dates = pd.to_datetime(df["Date"])
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    out_of_range = dates[(dates < start) | (dates > end)]
    if len(out_of_range) > 0:
        logger.warning(
            "%s has %d dates outside range [%s, %s]",
            label,
            len(out_of_range),
            start_date,
            end_date,
        )
        return False
    logger.info("%s: all %d dates within range", label, len(dates))
    return True


def validate_lat_lon_bounds(
    df: pd.DataFrame, bounds: dict[str, float], label: str
) -> bool:
    """Validate that latitude/longitude are within geographic bounds."""
    invalid_lat = df[
        (df["Latitude"] < bounds["min_lat"]) | (df["Latitude"] > bounds["max_lat"])
    ]
    invalid_lon = df[
        (df["Longitude"] < bounds["min_lon"])
        | (df["Longitude"] > bounds["max_lon"])
    ]
    total_invalid = len(invalid_lat) + len(invalid_lon)
    if total_invalid > 0:
        logger.warning(
            "%s has %d records outside lat/lon bounds", label, total_invalid
        )
        return False
    return True


def validate_value_ranges(
    df: pd.DataFrame, label: str
) -> dict[str, Any]:
    """Detect out-of-range values for climate variables."""
    issues: dict[str, Any] = {}
    if "Rainfall" in df.columns:
        neg_rain = (df["Rainfall"] < 0).sum()
        if neg_rain > 0:
            issues["negative_rainfall"] = int(neg_rain)
    if "MaxTemp" in df.columns:
        extreme_max = (df["MaxTemp"] > 50).sum()
        if extreme_max > 0:
            issues["max_temp_above_50"] = int(extreme_max)
        min_above_max = (
            "MinTemp" in df.columns and (df["MaxTemp"] < df["MinTemp"]).sum()
        )
        if min_above_max > 0:
            issues["max_temp_below_min_temp"] = int(min_above_max)
    if "MinTemp" in df.columns:
        extreme_min = (df["MinTemp"] < -5).sum()
        if extreme_min > 0:
            issues["min_temp_below_-5"] = int(extreme_min)
    if issues:
        logger.warning("%s value range issues: %s", label, issues)
    return issues


def detect_missing_values(df: pd.DataFrame, label: str) -> dict[str, int]:
    """Detect missing values per column."""
    missing = df.isnull().sum()
    missing_dict = missing[missing > 0].to_dict()
    if missing_dict:
        logger.warning("%s missing values: %s", label, missing_dict)
    return {str(k): int(v) for k, v in missing_dict.items()}


def detect_duplicates(df: pd.DataFrame, subset: list[str], label: str) -> int:
    """Detect duplicate records."""
    dups = df.duplicated(subset=subset, keep="first").sum()
    if dups > 0:
        logger.warning("%s has %d duplicate records", label, dups)
    return int(dups)


def generate_quality_report(
    dataset_files: dict[str, Path], config: dict[str, Any]
) -> dict[str, Any]:
    """Generate a comprehensive quality report for all datasets."""
    report: dict[str, Any] = {
        "pipeline": "data_pipeline",
        "phase": "validation",
        "timestamp": datetime.now().isoformat(),
        "datasets": {},
        "summary": {
            "total_datasets": len(dataset_files),
            "passed": 0,
            "failed": 0,
        },
    }
    expected_cols_map = {
        "rainfall": ["Date", "Latitude", "Longitude", "Rainfall"],
        "max_temp": ["Date", "Latitude", "Longitude", "MaxTemp"],
        "min_temp": ["Date", "Latitude", "Longitude", "MinTemp"],
    }
    start_date = config["date_range"]["start"]
    end_date = config["date_range"]["end"]
    bounds = config["karnataka_bounds"]
    for key, filepath in dataset_files.items():
        ds_report: dict[str, Any] = {
            "file": str(filepath),
            "checks": {},
        }
        exists = validate_file_exists(filepath)
        ds_report["checks"]["file_exists"] = exists

        if exists and filepath.suffix in (".csv", ".parquet"):
            try:
                df = (
                    pd.read_parquet(filepath)
                    if filepath.suffix == ".parquet"
                    else pd.read_csv(filepath)
                )
                ds_report["record_count"] = len(df)
            except Exception as e:
                logger.error("Failed to read %s: %s", filepath, e)
                ds_report["read_error"] = str(e)
                report["datasets"][key] = ds_report
                report["summary"]["failed"] += 1
                continue
        elif exists:
            ds_report["note"] = "Binary file, skipping column validation"
            report["datasets"][key] = ds_report
            report["summary"]["passed"] += 1
            continue
        else:
            report["datasets"][key] = ds_report
            report["summary"]["failed"] += 1
            continue

        expected_cols = expected_cols_map.get(key, [])
        ds_report["checks"]["missing_columns"] = validate_columns(
            df, expected_cols, key
        )
        ds_report["checks"]["date_range_ok"] = validate_date_range(
            df, start_date, end_date, key
        )
        ds_report["checks"]["lat_lon_bounds_ok"] = validate_lat_lon_bounds(
            df, bounds, key
        )
        ds_report["checks"]["value_range_issues"] = validate_value_ranges(df, key)
        ds_report["checks"]["missing_values"] = detect_missing_values(df, key)
        ds_report["checks"]["duplicate_count"] = detect_duplicates(
            df, expected_cols[:2] + ["Date"], key
        )

        all_ok = all(
            v is True or v == [] or v == {}
            for v in ds_report["checks"].values()
        )
        ds_report["passed"] = all_ok
        if all_ok:
            report["summary"]["passed"] += 1
        else:
            report["summary"]["failed"] += 1
        report["datasets"][key] = ds_report
    return report


def save_quality_report(
    report: dict[str, Any], output_path: str = "quality_report.json"
) -> str:
    """Save quality report to JSON file."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Quality report saved to %s", output)
    return str(output)
