from __future__ import annotations

import pandas as pd

from pipeline.export import export_datasets


class TestExportDatasets:
    def test_output_dir_from_config(self, tmp_path):
        df = pd.DataFrame(
            {
                "Date": ["2020-01-01", "2020-01-02", "2020-01-03"],
                "Rainfall": [1.0, 2.0, 3.0],
            }
        )
        config = {
            "data": {"processed_dir": str(tmp_path / "processed")},
            "pipeline": {"train_split": 0.7, "val_split": 0.15},
        }
        result = export_datasets(df, config)
        assert (tmp_path / "processed" / "training.csv").exists()
        assert set(result) == {"training", "validation", "testing"}
