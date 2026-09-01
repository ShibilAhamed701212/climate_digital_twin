from __future__ import annotations

import hashlib
import os
from pathlib import Path

from disaster_intelligence.domain.errors import TaskNotEnabledError, ValidationError
from disaster_intelligence.inference.runtimes import accelerator_hooks, selected_device

_MIN_WEIGHT_BYTES = 64

__all__ = [
    "WeightsRequiredRunner",
    "accelerator_hooks",
    "discover_weights",
    "inspect_weights",
    "selected_device",
    "weights_path",
    "weights_status",
]


def inspect_weights(path: Path, expected_sha256: str = "") -> dict[str, object]:
    if not path.is_file():
        raise ValidationError(f"Weights file not found: {path}")
    size = path.stat().st_size
    if size < _MIN_WEIGHT_BYTES:
        raise ValidationError("Weights file is too small to be a model checkpoint")
    head = path.read_bytes()[:8]
    kind = "unknown"
    suffix = path.suffix.lower()
    if head.startswith(b"PK") or head.startswith(b"\x80\x02") or head.startswith(b"\x80\x03"):
        kind = "torch"
    elif suffix == ".onnx":
        kind = "onnx"
    elif suffix in {".safetensors", ".st"}:
        kind = "safetensors"
    elif suffix == ".xml":
        kind = "openvino"
    elif suffix in {".engine", ".plan"}:
        kind = "tensorrt"
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    hexdigest = digest.hexdigest()
    if expected_sha256 and hexdigest.lower() != expected_sha256.lower():
        raise ValidationError("Weights SHA-256 does not match MODEL_WEIGHTS_*_SHA256")
    return {
        "path": str(path),
        "bytes": size,
        "kind": kind,
        "sha256": hexdigest,
        "inference_enabled": False,
    }


class WeightsRequiredRunner:
    """Registered learned model that does not run without a compatible checkpoint/loader."""

    model_id = "weights-required"
    model_version = "0"
    confidence_type = "unavailable"
    runtime_name = "none"
    fallback_used = False
    checkpoint_sha256 = ""
    device = "cpu"
    enabled = False

    def __init__(self, name: str, reason: str = "") -> None:
        self._name = name
        self.model_id = name
        self._reason = reason or (
            f"{name} is not enabled: place a compatible checkpoint and a validated loader"
        )

    def provenance(self) -> dict[str, str]:
        return {
            "flood": self._name,
            "requested": self._name,
            "runtime": self.runtime_name,
            "device": self.device,
            "checkpoint_sha256": self.checkpoint_sha256,
            "confidence_type": self.confidence_type,
            "fallback": "none",
            "reason": self._reason,
        }

    def run(self, task: str, mask_or_path: object, **kwargs: object) -> object:
        _ = task, mask_or_path, kwargs
        raise TaskNotEnabledError(self._reason)

    def mask_from_rows(self, rows: list[list[int]]) -> list[list[int]]:
        _ = rows
        raise TaskNotEnabledError(self._reason)

    def mask_from_path(self, path: str) -> list[list[int]]:
        _ = path
        raise TaskNotEnabledError(self._reason)

    def boundary_confidence(self, rows: list[list[int]], margin: int = 8) -> float | None:
        _ = rows, margin
        return None


_WEIGHT_SUFFIXES = {
    ".pt",
    ".pth",
    ".onnx",
    ".bin",
    ".safetensors",
    ".ckpt",
    ".engine",
    ".xml",
}


def discover_weights(name: str) -> Path | None:
    from disaster_intelligence.config import data_dir, env_str

    needle = name.lower().replace("-", "").replace("_", "")
    roots: list[Path] = []
    for raw in (
        env_str("MODEL_WEIGHTS_DIR", ""),
        env_str("MODEL_DIR", ""),
        "/models",
        str(data_dir() / "models"),
        "models/eo",
    ):
        if raw:
            roots.append(Path(raw))
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _WEIGHT_SUFFIXES:
                continue
            stem = path.stem.lower().replace("-", "").replace("_", "")
            parent = path.parent.name.lower().replace("-", "").replace("_", "")
            grand = path.parent.parent.name.lower().replace("-", "").replace("_", "")
            if needle in stem or needle in parent or needle in grand:
                return path
    return None


def weights_path(name: str) -> Path | None:
    from disaster_intelligence.config import env_str

    key = name.upper().replace("-", "_")
    for env_key in (f"MODEL_WEIGHTS_{key}", f"MODEL_{key}"):
        raw = env_str(env_key, "")
        if not raw:
            continue
        path = Path(raw)
        if path.is_file():
            return path
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in _WEIGHT_SUFFIXES:
                    return child
    return discover_weights(name)


def weights_status(name: str) -> dict[str, object]:
    path = weights_path(name)
    expected = os.environ.get(f"MODEL_WEIGHTS_{name.upper().replace('-', '_')}_SHA256", "")
    if path is None:
        return {"present": False, "valid": False, "inference_enabled": False}
    try:
        info = inspect_weights(path, expected)
        info["present"] = True
        info["valid"] = True
        return info
    except ValidationError as exc:
        return {
            "present": True,
            "valid": False,
            "inference_enabled": False,
            "error": str(exc),
        }
