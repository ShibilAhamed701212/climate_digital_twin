from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_VALID_STATUSES = {"EXPERIMENTAL", "VALIDATED", "REJECTED"}


class ProvenanceError(Exception):
    """Raised when a model lacks required provenance."""


class RegistryError(Exception):
    """Raised on invalid registry operations."""


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
        dataset_id: str | None = None,
        training_run_id: str | None = None,
        authenticity: str = "REAL",
        data_provenance: dict[str, Any] | None = None,
        status: str = "EXPERIMENTAL",
    ) -> dict[str, Any]:
        if status not in _VALID_STATUSES:
            raise RegistryError(f"Invalid status '{status}'. Valid: {sorted(_VALID_STATUSES)}")
        entry = {
            "name": name,
            "architecture": architecture,
            "version": version or "1.0.0",
            "checkpoint_path": checkpoint_path,
            "metrics": metrics or {},
            "config": config or {},
            "dataset_id": dataset_id or "",
            "training_run_id": training_run_id or "",
            "authenticity": authenticity,
            "data_provenance": data_provenance or {},
            "status": status,
            "registered_at": datetime.now().isoformat(),
        }
        self._models[name] = entry
        self._save()
        logger.info(
            "Registered model '%s' (v%s, %s, %s)", name, entry["version"], authenticity, status
        )
        return entry

    def get(self, name: str) -> dict[str, Any]:
        entry = self._models.get(name)
        if not entry:
            raise KeyError(f"Model '{name}' not found in registry")
        return entry

    def list_models(self) -> list[dict[str, Any]]:
        return list(self._models.values())

    def get_best(
        self,
        metric: str = "rmse",
        ascending: bool = True,
        require_validated: bool = False,
        require_real: bool = False,
    ) -> dict[str, Any]:
        candidates = [m for m in self._models.values() if metric in m.get("metrics", {})]
        if require_validated:
            candidates = [m for m in candidates if m.get("status") == "VALIDATED"]
        if require_real:
            candidates = [m for m in candidates if m.get("authenticity") == "REAL"]
        if not candidates:
            filters = []
            if require_real:
                filters.append("authenticity='REAL'")
            if require_validated:
                filters.append("status='VALIDATED'")
            raise KeyError(
                f"No models with metric '{metric}'"
                + (f" and {' and '.join(filters)}" if filters else "")
                + " in registry"
            )
        candidates.sort(key=lambda m: m["metrics"][metric], reverse=not ascending)
        return candidates[0]

    def update_metrics(self, name: str, metrics: dict[str, float]) -> dict[str, Any]:
        if name not in self._models:
            raise KeyError(f"Model '{name}' not found")
        self._models[name]["metrics"] = metrics
        self._models[name]["updated_at"] = datetime.now().isoformat()
        self._save()
        return self._models[name]

    def update_status(self, name: str, status: str, reason: str = "") -> dict[str, Any]:
        if name not in self._models:
            raise KeyError(f"Model '{name}' not found")
        if status not in _VALID_STATUSES:
            raise RegistryError(f"Invalid status '{status}'. Valid: {sorted(_VALID_STATUSES)}")
        self._models[name]["status"] = status
        self._models[name]["reason"] = reason
        self._models[name]["updated_at"] = datetime.now().isoformat()
        self._save()
        logger.info("Model '%s' status updated to %s (%s)", name, status, reason)
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
