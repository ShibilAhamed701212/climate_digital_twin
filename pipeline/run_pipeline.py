#!/usr/bin/env python3
"""
# LEGACY / SYNTHETIC / DEMO ONLY
# Use `python -m pipeline.ingest` for production real-data ingestion.
# This pipeline orchestrates download → validate → clean → features → export
# using potentially synthetic data. Preserved for backward compatibility.
# Do NOT call this from the production real-data pipeline.

Phase 2 — Data Pipeline Orchestrator.

Runs the complete data pipeline end-to-end:
  Download → Validation → Cleaning → Feature Engineering → Export

Usage:
    python pipeline/run_pipeline.py
"""

import logging
import sys
import time
from pathlib import Path

import yaml

from pipeline.clean import clean_dataset, merge_datasets
from pipeline.download import DataDownloader
from pipeline.export import export_datasets
from pipeline.feature_engine import FeatureEngine
from pipeline.features import engineer_features
from pipeline.validate import generate_quality_report, save_quality_report

CONFIG_PATH = "config/data_config.yaml"


def setup_logging(config: dict) -> logging.Logger:
    """Configure logging to file and console."""
    log_dir = Path(config["data"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "pipeline.log"
    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(log_file, mode="w")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


def run_pipeline() -> int:
    """Execute the full data pipeline and return exit code."""
    start_time = time.time()
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    logger = setup_logging(config)
    logger.info("=" * 60)
    logger.info("Phase 2 — Data Pipeline Started")
    logger.info("=" * 60)
    logger.info("Config loaded from %s", CONFIG_PATH)
    try:
        logger.info("--- Step 1/5: Download ---")
        downloader = DataDownloader(CONFIG_PATH)
        dataset_files = downloader.download_all()
        for key, path in dataset_files.items():
            logger.info("  %s -> %s", key, path)
        logger.info("--- Step 2/5: Validation ---")
        quality_report = generate_quality_report(dataset_files, config)
        _ = save_quality_report(quality_report)
        n_passed = quality_report["summary"]["passed"]
        n_failed = quality_report["summary"]["failed"]
        logger.info(
            "Quality report: %d passed, %d failed out of %d datasets",
            n_passed,
            n_failed,
            quality_report["summary"]["total_datasets"],
        )
        logger.info("--- Step 3/5: Cleaning ---")
        rainfall_path = dataset_files.get("rainfall")
        max_temp_path = dataset_files.get("max_temp")
        min_temp_path = dataset_files.get("min_temp")
        interim_dir = Path(config["data"]["interim_dir"])
        interim_dir.mkdir(parents=True, exist_ok=True)
        rainfall_df = None
        max_temp_df = None
        min_temp_df = None
        if rainfall_path and rainfall_path.suffix == ".parquet":
            rainfall_df = __import__("pandas").read_parquet(rainfall_path)
            logger.info("Loaded rainfall: %d records", len(rainfall_df))
        if max_temp_path and max_temp_path.suffix == ".parquet":
            max_temp_df = __import__("pandas").read_parquet(max_temp_path)
            logger.info("Loaded max_temp: %d records", len(max_temp_df))
        if min_temp_path and min_temp_path.suffix == ".parquet":
            min_temp_df = __import__("pandas").read_parquet(min_temp_path)
            logger.info("Loaded min_temp: %d records", len(min_temp_df))
        if rainfall_df is None or max_temp_df is None or min_temp_df is None:
            logger.error("Missing required datasets for merging")
            return 1
        merged_df = merge_datasets(rainfall_df, max_temp_df, min_temp_df)
        bounds = config["karnataka_bounds"]
        interim_path = interim_dir / "cleaned_data.parquet"
        cleaned_df = clean_dataset(merged_df, bounds, output_path=interim_path)
        logger.info("--- Step 4/5: Feature Engineering ---")
        features_dir = Path(config["data"]["interim_dir"])
        features_path = features_dir / "featured_data.parquet"
        featured_df = engineer_features(cleaned_df)

        # Enhance with BHAI FeatureEngine (advanced features)
        logger.info("--- Step 4b/5: Advanced Feature Engineering (BHAI) ---")
        try:
            engine = FeatureEngine()
            featured_df = engine.create_features(featured_df)
            n_new = len(engine.get_feature_names())
            logger.info("FeatureEngine added %d advanced features", n_new)
            for name, meta in engine.get_feature_metadata().items():
                logger.debug("  %s [%s]: %s", name, meta.feature_group, meta.description)
        except Exception as exc:
            logger.warning("FeatureEngine enhancement skipped: %s", exc)

        # Save featured data
        features_path.parent.mkdir(parents=True, exist_ok=True)
        featured_df.to_parquet(features_path, index=False)
        logger.info("Features saved to %s (%d cols)", features_path, len(featured_df.columns))
        logger.info("--- Step 5/5: Export ---")
        processed_dir = Path(config["data"]["processed_dir"])
        exported = export_datasets(featured_df, config, output_dir=processed_dir)
        for split_name, filepath in exported.items():
            logger.info("  %s -> %s", split_name, filepath)
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info("Phase 2 Pipeline Complete in %.2f seconds", elapsed)
        logger.info("=" * 60)
        return 0
    except Exception:
        logger.exception("Pipeline failed with unhandled exception")
        elapsed = time.time() - start_time
        logger.info("Pipeline failed after %.2f seconds", elapsed)
        return 1


if __name__ == "__main__":
    sys.exit(run_pipeline())
