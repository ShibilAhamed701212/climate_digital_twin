from __future__ import annotations

import yaml

from pipeline.features import load_config


class TestLoadConfig:
    def test_loads_yaml(self, tmp_path):
        cfg = {"key": "value", "nested": {"a": 1}}
        p = tmp_path / "config.yaml"
        with open(p, "w") as f:
            yaml.dump(cfg, f)
        assert load_config(str(p)) == cfg
