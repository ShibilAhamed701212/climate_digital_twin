from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from disaster_intelligence.inference.changeformer import CHANGEFORMER_FLOOD_REASON
from disaster_intelligence.inference.factory import LEARNED_MODELS
from disaster_intelligence.inference.learned import weights_status
from disaster_intelligence.inference.mask2former import MASK2FORMER_REASON
from disaster_intelligence.inference.runtimes import (
    accelerator_hooks,
    selected_device,
    selected_runtime,
)
from disaster_intelligence.inference.segformer import SEGFORMER_REASON
from disaster_intelligence.inference.unet import UNET_MODEL_ID

_CARD_DIR = Path(__file__).resolve().parent / "cards"
_MANIFEST = Path(__file__).resolve().parent / "manifest.yaml"

_DISABLE_REASON = {
    "segformer": SEGFORMER_REASON,
    "mask2former": MASK2FORMER_REASON,
    "changeformer": CHANGEFORMER_FLOOD_REASON,
}


def load_manifest() -> dict[str, Any]:
    if not _MANIFEST.exists():
        return {"models": []}
    with _MANIFEST.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"models": []}


def load_card(model_id: str) -> dict[str, Any]:
    path = _CARD_DIR / f"{model_id}.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def catalog() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    thresh = load_card("s1-threshold-v0")
    items.append(
        {
            "id": "s1-threshold-v0",
            "task": "flood_extent",
            "version": str(thresh.get("version") or "0"),
            "framework": "numpy-threshold",
            "license": "Apache-2.0",
            "input": "single-band uint8 TIFF (SAR DN or optical)",
            "output": "binary water mask",
            "enabled": True,
            "confidence_type": "threshold_boundary_agreement",
            "runtime": "numpy",
            "device": "cpu",
        }
    )
    unet_status = weights_status("unet")
    hooks = accelerator_hooks()
    unet_enabled = bool(unet_status.get("valid")) and bool(hooks.get("torch"))
    items.append(
        {
            "id": "unet",
            "model_id": UNET_MODEL_ID,
            "task": "flood_extent",
            "version": "0",
            "framework": "torch-smp-unet-resnet34",
            "license": "MIT",
            "input": "Sentinel-1 VV+VH sigma0 dB (2 channels), 512 tiles",
            "output": "binary water mask (0 dry, 1 water)",
            "enabled": unet_enabled,
            "reason": None
            if unet_enabled
            else (
                "Checkpoint and/or torch+segmentation_models_pytorch required. "
                "Current 1-band uint8 ingest cannot scientifically feed this model."
            ),
            "confidence_type": "softmax_margin",
            "sensor": "sentinel-1",
            "dataset": "Sen1Floods11",
            "input_channels": 2,
            "classes": 2,
            "weights": unet_status,
        }
    )
    for name in sorted(LEARNED_MODELS - {"unet"}):
        status = weights_status(name)
        card = load_card(name)
        items.append(
            {
                "id": name,
                "task": card.get("task") or "flood_extent",
                "version": str(card.get("version") or "0"),
                "framework": card.get("framework") or "weights-required",
                "license": card.get("license") or "not-bundled",
                "input": card.get("input") or "validated GeoTIFF",
                "output": card.get("output") or "binary water mask",
                "enabled": False,
                "reason": _DISABLE_REASON.get(name, "no compatible pretrained EO checkpoint"),
                "confidence_type": "unavailable",
                "weights": status,
            }
        )
    return {
        "items": items,
        "active_flood": os.environ.get("MODEL_FLOOD", "threshold"),
        "device": selected_device(),
        "runtime": selected_runtime(),
        "accelerators": hooks,
        "manifest": load_manifest(),
    }
