from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(self, registry_path: str = "models/registry/metadata.json") -> None:
        self._path = Path(registry_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._models: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    self._models = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load registry from %s: %s", self._path, e)
                self._models = {}

    def _save(self) -> None:
        with open(self._path, "w") as f:
            json.dump(self._models, f, indent=2, default=str)

    def register(
        self,
        name: str,
        architecture: str,
        checkpoint_path: str,
        metrics: dict[str, float] | None = None,
        config: dict[str, Any] | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        entry = {
            "name": name,
            "architecture": architecture,
            "version": version or "1.0.0",
            "checkpoint_path": checkpoint_path,
            "metrics": metrics or {},
            "config": config or {},
            "registered_at": datetime.now().isoformat(),
        }
        self._models[name] = entry
        self._save()
        logger.info("Registered model '%s' (v%s)", name, entry["version"])
        return entry

    def get(self, name: str) -> dict[str, Any]:
        entry = self._models.get(name)
        if not entry:
            raise KeyError(f"Model '{name}' not found in registry")
        return entry

    def list_models(self) -> list[dict[str, Any]]:
        return list(self._models.values())

    def get_best(self, metric: str = "rmse", ascending: bool = True) -> dict[str, Any]:
        candidates = [m for m in self._models.values() if metric in m.get("metrics", {})]
        if not candidates:
            raise KeyError(f"No models with metric '{metric}' in registry")
        candidates.sort(key=lambda m: m["metrics"][metric], reverse=not ascending)
        return candidates[0]

    def update_metrics(self, name: str, metrics: dict[str, float]) -> dict[str, Any]:
        if name not in self._models:
            raise KeyError(f"Model '{name}' not found")
        self._models[name]["metrics"] = metrics
        self._models[name]["updated_at"] = datetime.now().isoformat()
        self._save()
        return self._models[name]

    def delete(self, name: str) -> bool:
        if name not in self._models:
            return False
        del self._models[name]
        self._save()
        logger.info("Deleted model '%s' from registry", name)
        return True

    def contains(self, name: str) -> bool:
        return name in self._models

    def get_available_architectures(self) -> list[str]:
        return list({m["architecture"] for m in self._models.values()})

    def count(self) -> int:
        return len(self._models)
