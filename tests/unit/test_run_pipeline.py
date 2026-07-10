"""Tests for pipeline/run_pipeline.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_config() -> dict:
    return {
        "data": {
            "log_dir": "logs",
            "interim_dir": "data/interim",
            "processed_dir": "data/processed",
        },
        "karnataka_bounds": {
            "lat_min": 10.0,
            "lat_max": 20.0,
            "lon_min": 70.0,
            "lon_max": 80.0,
        },
    }


class TestRunPipeline:
    @patch("pipeline.run_pipeline.yaml")
    @patch("pipeline.run_pipeline.DataDownloader")
    @patch("pipeline.run_pipeline.generate_quality_report")
    @patch("pipeline.run_pipeline.save_quality_report")
    @patch("pipeline.run_pipeline.merge_datasets")
    @patch("pipeline.run_pipeline.clean_dataset")
    @patch("pipeline.run_pipeline.engineer_features")
    @patch("pipeline.run_pipeline.export_datasets")
    def test_run_pipeline_success(
        self,
        _mock_export: MagicMock,
        _mock_engineer: MagicMock,
        _mock_clean: MagicMock,
        _mock_merge: MagicMock,
        _mock_save_report: MagicMock,
        mock_gen_report: MagicMock,
        mock_downloader_cls: MagicMock,
        mock_yaml: MagicMock,
        mock_config: dict,
    ) -> None:
        from pipeline.run_pipeline import run_pipeline

        mock_yaml.safe_load.return_value = mock_config

        downloader_instance = MagicMock()
        downloader_instance.download_all.return_value = {
            "rainfall": Path("data/raw/rainfall.parquet"),
            "max_temp": Path("data/raw/max_temp.parquet"),
            "min_temp": Path("data/raw/min_temp.parquet"),
        }
        mock_downloader_cls.return_value = downloader_instance

        mock_gen_report.return_value = {
            "summary": {"passed": 3, "failed": 0, "total_datasets": 3},
        }

        import pandas as pd

        mock_df = pd.DataFrame(
            {
                "DATE": ["2020-01-01", "2020-01-02"],
                "Rainfall": [10.0, 20.0],
                "MaxTemp": [30.0, 32.0],
                "MinTemp": [20.0, 22.0],
            }
        )

        with (
            patch("pandas.read_parquet", return_value=mock_df),
        ):
            exit_code = run_pipeline()

        assert exit_code == 0
        mock_downloader_cls.assert_called_once()

    @patch("pipeline.run_pipeline.yaml")
    def test_run_pipeline_missing_datasets(self, mock_yaml: MagicMock, mock_config: dict) -> None:
        from pipeline.run_pipeline import run_pipeline

        mock_yaml.safe_load.return_value = mock_config

        with (
            patch("pipeline.run_pipeline.DataDownloader") as mock_dl_cls,
            patch("pipeline.run_pipeline.generate_quality_report"),
            patch("pipeline.run_pipeline.save_quality_report"),
            patch("pandas.read_parquet", return_value=None),
        ):
            downloader = MagicMock()
            downloader.download_all.return_value = {
                "rainfall": Path("data/raw/rainfall.parquet"),
            }
            mock_dl_cls.return_value = downloader

            exit_code = run_pipeline()
            assert exit_code == 1

    def test_setup_logging(self, tmp_path: Path) -> None:
        from pipeline.run_pipeline import setup_logging

        config = {"data": {"log_dir": str(tmp_path / "logs")}}
        logger = setup_logging(config)
        assert logger.name == "pipeline"
        assert (tmp_path / "logs" / "pipeline.log").parent.exists()


class TestPipelineImports:
    def test_import_pipeline_modules(self) -> None:
        import pipeline.clean
        import pipeline.download
        import pipeline.export
        import pipeline.features
        import pipeline.run_pipeline
        import pipeline.validate

        assert hasattr(pipeline.run_pipeline, "run_pipeline")
        assert hasattr(pipeline.clean, "clean_dataset")
        assert hasattr(pipeline.clean, "merge_datasets")
        assert hasattr(pipeline.download, "DataDownloader")
        assert hasattr(pipeline.export, "export_datasets")
        assert hasattr(pipeline.features, "engineer_features")
        assert hasattr(pipeline.validate, "generate_quality_report")
        assert hasattr(pipeline.validate, "save_quality_report")
