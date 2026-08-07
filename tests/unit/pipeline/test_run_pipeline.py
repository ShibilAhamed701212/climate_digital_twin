from __future__ import annotations

from unittest.mock import MagicMock, patch

from pipeline.run_pipeline import run_pipeline

CONFIG = {
    "data": {
        "log_dir": "/tmp/logs",
        "interim_dir": "/tmp/interim",
        "processed_dir": "/tmp/processed",
    },
    "pipeline": {"train_split": 0.7, "val_split": 0.15},
    "karnataka_bounds": {"min_lat": 10, "max_lat": 15, "min_lon": 75, "max_lon": 80},
}


class TestRunPipeline:
    @patch("builtins.open")
    @patch("pipeline.run_pipeline.Path")
    @patch("pipeline.run_pipeline.save_quality_report")
    @patch("pipeline.run_pipeline.generate_quality_report")
    @patch("pipeline.run_pipeline.DataDownloader")
    @patch("builtins.__import__")
    @patch("pipeline.run_pipeline.yaml.safe_load")
    def test_missing_datasets_returns_1(
        self, mock_yaml, _mock_import, mock_dl, mock_report, _mock_save, _mock_path, _mock_open
    ):
        mock_yaml.return_value = CONFIG
        mock_report.return_value = {"summary": {"passed": 0, "failed": 0, "total_datasets": 0}}
        dl_result = {
            "rainfall": MagicMock(suffix=".parquet"),
            "min_temp": MagicMock(suffix=".parquet"),
        }
        mock_dl.return_value.download_all.return_value = dl_result
        assert run_pipeline() == 1

    @patch("builtins.open")
    @patch("pipeline.run_pipeline.Path")
    @patch("pipeline.run_pipeline.FeatureEngine")
    @patch("pipeline.run_pipeline.export_datasets")
    @patch("pipeline.run_pipeline.engineer_features")
    @patch("pipeline.run_pipeline.clean_dataset")
    @patch("pipeline.run_pipeline.merge_datasets")
    @patch("pipeline.run_pipeline.save_quality_report")
    @patch("pipeline.run_pipeline.generate_quality_report")
    @patch("pipeline.run_pipeline.DataDownloader")
    @patch("builtins.__import__")
    @patch("pipeline.run_pipeline.yaml.safe_load")
    def test_feature_engine_exception_continues(
        self,
        mock_yaml,
        mock_import,
        mock_dl,
        mock_report,
        _mock_save,
        mock_merge,
        mock_clean,
        mock_eng,
        mock_export,
        mock_fe,
        _mock_path,
        _mock_open,
    ):
        mock_yaml.return_value = CONFIG
        mock_import.return_value.read_parquet.return_value = MagicMock()
        dl_result = {k: MagicMock(suffix=".parquet") for k in ("rainfall", "max_temp", "min_temp")}
        mock_dl.return_value.download_all.return_value = dl_result
        mock_report.return_value = {"summary": {"passed": 3, "failed": 0, "total_datasets": 3}}
        mock_merge.return_value = MagicMock()
        mock_clean.return_value = MagicMock()
        mock_eng.return_value = MagicMock()
        mock_export.return_value = {"training": "t.csv", "validation": "v.csv", "testing": "e.csv"}
        mock_fe.side_effect = Exception("FeatureEngine error")
        assert run_pipeline() == 0

    @patch("builtins.open")
    @patch("pipeline.run_pipeline.Path")
    @patch("pipeline.run_pipeline.FeatureEngine")
    @patch("pipeline.run_pipeline.export_datasets")
    @patch("pipeline.run_pipeline.engineer_features")
    @patch("pipeline.run_pipeline.clean_dataset")
    @patch("pipeline.run_pipeline.merge_datasets")
    @patch("pipeline.run_pipeline.save_quality_report")
    @patch("pipeline.run_pipeline.generate_quality_report")
    @patch("pipeline.run_pipeline.DataDownloader")
    @patch("builtins.__import__")
    @patch("pipeline.run_pipeline.yaml.safe_load")
    def test_full_pipeline_export_logging(
        self,
        mock_yaml,
        mock_import,
        mock_dl,
        mock_report,
        _mock_save,
        mock_merge,
        mock_clean,
        mock_eng,
        mock_export,
        mock_fe,
        _mock_path,
        _mock_open,
    ):
        mock_yaml.return_value = CONFIG
        mock_import.return_value.read_parquet.return_value = MagicMock()
        dl_result = {k: MagicMock(suffix=".parquet") for k in ("rainfall", "max_temp", "min_temp")}
        mock_dl.return_value.download_all.return_value = dl_result
        mock_report.return_value = {"summary": {"passed": 3, "failed": 0, "total_datasets": 3}}
        mock_merge.return_value = MagicMock()
        mock_clean.return_value = MagicMock()
        mock_eng.return_value = MagicMock()
        mock_export.return_value = {"training": "t.csv", "validation": "v.csv", "testing": "e.csv"}
        fe_instance = MagicMock()
        fe_instance.get_feature_names.return_value = ["f1"]
        fe_instance.get_feature_metadata.return_value = {
            "f1": MagicMock(feature_group="g", description="d"),
        }
        mock_fe.return_value = fe_instance
        assert run_pipeline() == 0
