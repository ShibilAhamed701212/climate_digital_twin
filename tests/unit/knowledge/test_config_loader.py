"""Tests covering uncovered lines in knowledge/config_loader.py."""

import os
import tempfile

import yaml


class TestConfigLoaderExtended:
    def test_section_not_in_defaults(self):
        from knowledge.config_loader import load_rag_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"custom_section": {"key": "value"}}, f)
            f.flush()
            path = f.name
        try:
            cfg = load_rag_config(path)
            assert cfg["custom_section"] == {"key": "value"}
            assert cfg["rag"]["chunk_size"] == 700
        finally:
            os.unlink(path)
