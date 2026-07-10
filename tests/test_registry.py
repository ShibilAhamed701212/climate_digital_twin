from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from models.registry import ModelRegistry


@pytest.fixture
def registry_path() -> str:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def registry(registry_path: str) -> ModelRegistry:
    return ModelRegistry(registry_path=registry_path)


class TestModelRegistry:
    def test_register_and_get(self, registry: ModelRegistry):
        entry = registry.register(
            name="transformer",
            architecture="Transformer",
            checkpoint_path="models/checkpoints/transformer_best.pt",
            metrics={"rmse": 4.5284, "r2": 0.8735},
        )
        assert entry["name"] == "transformer"
        assert entry["architecture"] == "Transformer"
        assert "registered_at" in entry

        retrieved = registry.get("transformer")
        assert retrieved["name"] == "transformer"
        assert retrieved["metrics"]["rmse"] == 4.5284

    def test_get_missing_raises(self, registry: ModelRegistry):
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_list_models(self, registry: ModelRegistry):
        registry.register("a", "MLP", "a.pt")
        registry.register("b", "LSTM", "b.pt")
        models = registry.list_models()
        assert len(models) == 2
        names = {m["name"] for m in models}
        assert names == {"a", "b"}

    def test_get_best_by_rmse(self, registry: ModelRegistry):
        registry.register("m1", "MLP", "m1.pt", metrics={"rmse": 5.0})
        registry.register("m2", "LSTM", "m2.pt", metrics={"rmse": 4.0})
        registry.register("m3", "Transformer", "m3.pt", metrics={"rmse": 3.0})
        best = registry.get_best(metric="rmse")
        assert best["name"] == "m3"

    def test_get_best_ascending_false(self, registry: ModelRegistry):
        registry.register("m1", "MLP", "m1.pt", metrics={"r2": 0.8})
        registry.register("m2", "LSTM", "m2.pt", metrics={"r2": 0.9})
        best = registry.get_best(metric="r2", ascending=False)
        assert best["name"] == "m2"

    def test_get_best_no_metric_raises(self, registry: ModelRegistry):
        registry.register("m1", "MLP", "m1.pt")
        with pytest.raises(KeyError, match="No models with metric"):
            registry.get_best(metric="rmse")

    def test_update_metrics(self, registry: ModelRegistry):
        registry.register("m1", "MLP", "m1.pt", metrics={"rmse": 5.0})
        registry.update_metrics("m1", {"rmse": 4.5, "r2": 0.88})
        updated = registry.get("m1")
        assert updated["metrics"]["rmse"] == 4.5
        assert updated["metrics"]["r2"] == 0.88
        assert "updated_at" in updated

    def test_update_metrics_missing_raises(self, registry: ModelRegistry):
        with pytest.raises(KeyError, match="not found"):
            registry.update_metrics("nonexistent", {})

    def test_delete(self, registry: ModelRegistry):
        registry.register("m1", "MLP", "m1.pt")
        assert registry.contains("m1")
        assert registry.delete("m1") is True
        assert not registry.contains("m1")

    def test_delete_missing(self, registry: ModelRegistry):
        assert registry.delete("nonexistent") is False

    def test_contains(self, registry: ModelRegistry):
        registry.register("m1", "MLP", "m1.pt")
        assert registry.contains("m1")
        assert not registry.contains("nonexistent")

    def test_get_available_architectures(self, registry: ModelRegistry):
        registry.register("a", "MLP", "a.pt")
        registry.register("b", "LSTM", "b.pt")
        registry.register("c", "MLP", "c.pt")
        arches = registry.get_available_architectures()
        assert sorted(arches) == sorted(["MLP", "LSTM"])

    def test_count(self, registry: ModelRegistry):
        assert registry.count() == 0
        registry.register("a", "MLP", "a.pt")
        assert registry.count() == 1
        registry.register("b", "LSTM", "b.pt")
        assert registry.count() == 2

    def test_persistence(self, registry_path: str):
        reg1 = ModelRegistry(registry_path=registry_path)
        reg1.register("m1", "MLP", "m1.pt", metrics={"rmse": 5.0})

        reg2 = ModelRegistry(registry_path=registry_path)
        assert reg2.contains("m1")
        assert reg2.get("m1")["metrics"]["rmse"] == 5.0

    def test_corrupted_file_starts_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not valid json")
            path = f.name
        try:
            reg = ModelRegistry(registry_path=path)
            assert reg.count() == 0
        finally:
            Path(path).unlink(missing_ok=True)
