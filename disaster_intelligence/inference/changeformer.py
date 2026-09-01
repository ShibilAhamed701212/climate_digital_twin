from __future__ import annotations

from pathlib import Path
from typing import Any

from disaster_intelligence.domain.errors import TaskNotEnabledError, ValidationError
from disaster_intelligence.inference.learned import (
    WeightsRequiredRunner,
    inspect_weights,
    weights_path,
)

CHANGEFORMER_FLOOD_REASON = (
    "ChangeFormer is a before/after optical change-detection model (LEVIR-CD RGB, 256x256), "
    "not a Sentinel-1 flood mapper. It is not used as MODEL_FLOOD."
)

CHANGEFORMER_INFER_REASON = (
    "ChangeFormer checkpoint may be present, but inference requires the official "
    "ChangeFormerV6 architecture from https://github.com/wgcban/ChangeFormer "
    "(custom net_G, not a generic segmentation_models_pytorch model). "
    "Set CHANGEFORMER_CODE_DIR to that repo to enable optional research inference. "
    "Pretrained weights are released for non-commercial research; contact the authors "
    "for commercial use."
)


def changeformer_weights() -> Path | None:
    path = weights_path("changeformer")
    if path is None:
        # official zip extracts best_ckpt.pt
        from disaster_intelligence.inference.learned import discover_weights

        path = discover_weights("best_ckpt") or discover_weights("changeformer")
    return path


class ChangeFormerFloodRunner(WeightsRequiredRunner):
    """Reject flood-pipeline use; ChangeFormer is not a flood detector."""

    model_id = "changeformer"
    model_version = "0"
    confidence_type = "unavailable"
    enabled = False
    disable_reason = CHANGEFORMER_FLOOD_REASON

    def __init__(self) -> None:
        super().__init__("changeformer", reason=CHANGEFORMER_FLOOD_REASON)


class ChangeFormerRunner:
    """Optional optical RGB change detection. Not used by the flood job."""

    model_id = "changeformer-levir-v6"
    model_version = "0"
    confidence_type = "softmax_margin"
    enabled = False

    def validate_pair(
        self,
        before: list[list[list[float]]],
        after: list[list[list[float]]],
    ) -> None:
        if not before or not after:
            raise ValidationError("ChangeFormer requires pre-event and post-event images")
        if len(before) != 3 or len(after) != 3:
            raise ValidationError(
                "ChangeFormer LEVIR checkpoint expects 3-channel RGB (not SAR VV/VH)",
                "WRONG_INPUT_CHANNELS",
            )
        if len(before[0]) != len(after[0]) or len(before[0][0]) != len(after[0][0]):
            raise ValidationError("Before/after spatial size must match")

    def change_mask(
        self,
        before: list[list[list[float]]],
        after: list[list[list[float]]],
    ) -> list[list[int]]:
        self.validate_pair(before, after)
        path = changeformer_weights()
        if path is None:
            raise TaskNotEnabledError(
                "ChangeFormer weights not found. Download the official LEVIR zip from "
                "https://github.com/wgcban/ChangeFormer/releases/tag/v0.1.0"
            )
        inspect_weights(path)
        _ = after
        raise TaskNotEnabledError(CHANGEFORMER_INFER_REASON)

    def geospatial_placeholder(self) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [],
            "note": "Change polygons are not produced until ChangeFormerV6 inference is enabled",
        }
