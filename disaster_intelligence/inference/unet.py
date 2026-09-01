from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from disaster_intelligence.domain.entities import InferenceResult
from disaster_intelligence.domain.enums import QualityFlag
from disaster_intelligence.domain.errors import TaskNotEnabledError, ValidationError
from disaster_intelligence.inference.learned import inspect_weights, weights_path
from disaster_intelligence.inference.runtimes import (
    flood_fallback_to_threshold,
    oom_fallback_to_cpu,
    selected_device,
    selected_runtime,
    tile_size,
    vram_batch_size,
)
from disaster_intelligence.inference.threshold import S1ThresholdFloodRunner
from disaster_intelligence.preprocessing.sentinel1 import VH_MEAN, VH_STD, VV_MEAN, VV_STD

UNET_MODEL_ID = "unet-sen1floods11-resnet34"
UNET_VERSION = "0"
EXPECTED_IN_CHANNELS = 2
EXPECTED_CLASSES = 2


def _threshold(dn_max: int) -> S1ThresholdFloodRunner:
    return S1ThresholdFloodRunner(dn_max=dn_max)


def _require_weights() -> Path:
    path = weights_path("unet")
    if path is None:
        raise TaskNotEnabledError(
            "U-Net weights are not present. Set MODEL_WEIGHTS_UNET or place "
            "model.pt under MODEL_WEIGHTS_DIR/flood/unet/ "
            "(official source: Hugging Face Governor6191/sar-flood-extent-unet-resnet34)."
        )
    inspect_weights(path)
    return path


class UNetFloodRunner:
    """Sentinel-1 VV+VH U-Net (Sen1Floods11). Single-band uint8 DN is not a valid input."""

    model_id = UNET_MODEL_ID
    model_version = UNET_VERSION
    confidence_type = "softmax_margin"
    runtime_name = "torch"

    def __init__(self, dn_max: int = 80) -> None:
        self._dn_max = dn_max
        self._model: Any = None
        self.fallback_used = False
        self.checkpoint_sha256 = ""
        self.device = selected_device()
        self.runtime_name = selected_runtime()
        self.last_flags: list[str] = []
        self.last_confidence: float | None = None
        self.fallback_reason = ""
        self.processing_ms = 0.0

    def provenance(self) -> dict[str, str]:
        actual = "s1-threshold-v0" if self.fallback_used else self.model_id
        return {
            "flood": actual,
            "requested": "unet",
            "requested_model": "unet",
            "actual_model": actual,
            "runtime": self.runtime_name if not self.fallback_used else "numpy",
            "device": self.device if not self.fallback_used else "cpu",
            "checkpoint_sha256": self.checkpoint_sha256,
            "confidence_type": (
                "threshold_boundary_agreement" if self.fallback_used else self.confidence_type
            ),
            "fallback": "threshold" if self.fallback_used else "none",
            "fallback_used": "true" if self.fallback_used else "false",
            "fallback_reason": self.fallback_reason,
            "sensor": "sentinel-1",
            "polarization": "VV+VH" if not self.fallback_used else "unknown",
            "input_channels": "2" if not self.fallback_used else "1",
            "processing_ms": str(int(self.processing_ms)),
        }

    def _maybe_fallback(self, rows: list[list[int]], reason: str) -> list[list[int]]:
        self.fallback_reason = reason
        if not flood_fallback_to_threshold():
            raise TaskNotEnabledError(reason)
        self.fallback_used = True
        self.last_flags = [QualityFlag.THRESHOLD_FALLBACK.value]
        return _threshold(self._dn_max).mask_from_rows(rows)

    def run(self, task: str, mask_or_path: object, **kwargs: object) -> InferenceResult:
        _ = kwargs
        if task != "flood_extent":
            raise ValueError(f"Unsupported task {task}")
        if not isinstance(mask_or_path, list):
            raise ValidationError("U-Net run() expects an in-memory mask or VV/VH arrays")
        mask = mask_or_path
        water = sum(1 for row in mask for v in row if v > 0)
        total = sum(len(row) for row in mask) or 1
        return InferenceResult(
            task=task,
            metrics={"water_pct": water / total, "water_pixels": water, "total_pixels": total},
            output_uris=[],
            duration_ms=0.0,
            quality_flags=list(self.last_flags) or [QualityFlag.S1_ONLY.value],
        )

    def mask_from_rows(self, rows: list[list[int]]) -> list[list[int]]:
        self.fallback_used = False
        self.last_flags = []
        return self._maybe_fallback(
            rows,
            "U-Net requires two Sentinel-1 channels (VV, VH) as sigma0 dB. "
            "Provide a VV+VH stack (.s1.json sidecar or 2-channel float TIFF), "
            "or set MODEL_FLOOD=threshold / MODEL_FLOOD_FALLBACK=threshold.",
        )

    def mask_from_path(self, path: str) -> list[list[int]]:
        from disaster_intelligence.domain.geotiff import read_uint8_tiff

        rows, _, _ = read_uint8_tiff(Path(path))
        return self.mask_from_rows(rows)

    def boundary_confidence(self, rows: list[list[int]], margin: int = 8) -> float | None:
        if self.fallback_used:
            return _threshold(self._dn_max).boundary_confidence(rows, margin)
        return self.last_confidence

    def mask_from_vv_vh(
        self,
        vv: list[list[float]],
        vh: list[list[float]],
        *,
        already_standardized: bool = False,
    ) -> list[list[int]]:
        self.fallback_used = False
        self.fallback_reason = ""
        self.last_confidence = None
        self.last_flags = [QualityFlag.S1_ONLY.value, QualityFlag.S1_VV_VH.value]
        if not vv or not vh or len(vv) != len(vh) or len(vv[0]) != len(vh[0]):
            raise ValidationError("VV and VH arrays must have the same non-empty shape")
        try:
            path = _require_weights()
            info = inspect_weights(path)
            self.checkpoint_sha256 = str(info["sha256"])
        except (TaskNotEnabledError, ValidationError) as exc:
            rows = [[int(max(0, min(255, round(v)))) for v in row] for row in vv]
            return self._maybe_fallback(rows, str(exc))
        try:
            started = time.perf_counter()
            mask = self._infer_torch(vv, vh, already_standardized=already_standardized)
            self.processing_ms = (time.perf_counter() - started) * 1000.0
            return mask
        except TaskNotEnabledError as exc:
            rows = [[int(max(0, min(255, round(v)))) for v in row] for row in vv]
            return self._maybe_fallback(rows, str(exc))

    def _load_torch(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            import segmentation_models_pytorch as smp
            import torch
        except Exception as exc:
            raise TaskNotEnabledError(
                "U-Net inference needs torch and segmentation_models_pytorch "
                f"(optional extra; CPU DIE image does not bundle them): {exc}"
            ) from exc
        path = _require_weights()
        device = "cuda" if selected_device() == "cuda" else "cpu"
        if device == "cuda":
            try:
                if not torch.cuda.is_available():
                    device = "cpu"
            except Exception:
                device = "cpu"
        self.device = device
        ckpt = torch.load(str(path), map_location=device, weights_only=False)
        state = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt
        model = smp.create_model(
            "unet",
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=EXPECTED_IN_CHANNELS,
            classes=EXPECTED_CLASSES,
        )
        model.load_state_dict(state)
        model.to(device)
        model.eval()
        self._model = model
        self.runtime_name = "torch"
        return model

    def _infer_torch(
        self,
        vv: list[list[float]],
        vh: list[list[float]],
        *,
        already_standardized: bool,
    ) -> list[list[int]]:
        import numpy as np
        import torch

        model = self._load_torch()
        arr = np.stack(
            [
                np.asarray(vv, dtype=np.float32),
                np.asarray(vh, dtype=np.float32),
            ],
            axis=0,
        )
        if arr.shape[0] != EXPECTED_IN_CHANNELS:
            raise ValidationError(
                f"U-Net expects {EXPECTED_IN_CHANNELS} input channels (VV, VH)",
                "WRONG_INPUT_CHANNELS",
            )
        if not already_standardized:
            arr[0] = (arr[0] - np.float32(VV_MEAN)) / np.float32(VV_STD)
            arr[1] = (arr[1] - np.float32(VH_MEAN)) / np.float32(VH_STD)
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        height, width = int(arr.shape[1]), int(arr.shape[2])
        tile = tile_size()
        batch = vram_batch_size()
        out = np.zeros((height, width), dtype=np.uint8)
        patches: list[np.ndarray] = []
        coords: list[tuple[int, int, int, int]] = []
        for y in range(0, height, tile):
            for x in range(0, width, tile):
                patch = arr[:, y : y + tile, x : x + tile]
                ph, pw = int(patch.shape[1]), int(patch.shape[2])
                if ph < tile or pw < tile:
                    padded = np.zeros((2, tile, tile), dtype=np.float32)
                    padded[:, :ph, :pw] = patch
                    patch = padded
                patches.append(patch)
                coords.append((y, x, ph, pw))
        device = self.device if self.device in {"cpu", "cuda"} else "cpu"
        amp = device == "cuda"
        margins: list[float] = []
        try:
            with torch.no_grad():
                for i in range(0, len(patches), batch):
                    chunk = np.stack(patches[i : i + batch])
                    tensor = torch.from_numpy(chunk).to(device)
                    if amp:
                        with torch.autocast(device_type="cuda", enabled=True):
                            logits = model(tensor)
                    else:
                        logits = model(tensor)
                    if int(logits.shape[1]) != EXPECTED_CLASSES:
                        raise ValidationError(
                            f"U-Net output classes {logits.shape[1]} != {EXPECTED_CLASSES}",
                            "WRONG_OUTPUT_CLASSES",
                        )
                    pred = logits.argmax(dim=1).detach().cpu().numpy().astype(np.uint8)
                    prob = torch.softmax(logits.float(), dim=1)
                    margin = (prob[:, 1] - prob[:, 0]).detach().cpu().numpy()
                    for j, (y, x, ph, pw) in enumerate(coords[i : i + batch]):
                        out[y : y + ph, x : x + pw] = pred[j, :ph, :pw]
                        margins.append(float(margin[j, :ph, :pw].mean()))
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() and device == "cuda":
                if not oom_fallback_to_cpu():
                    raise TaskNotEnabledError(
                        "U-Net CUDA out of memory. Set MODEL_OOM_FALLBACK=cpu for an explicit "
                        "CPU retry, or MODEL_DEVICE=cpu."
                    ) from exc
                self.device = "cpu"
                self._model = None
                return self._infer_torch(
                    vv, vh, already_standardized=already_standardized
                )
            raise TaskNotEnabledError(f"U-Net inference failed: {exc}") from exc
        if margins:
            self.last_confidence = round(sum(margins) / len(margins), 4)
        return out.tolist()
