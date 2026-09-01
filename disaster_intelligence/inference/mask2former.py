from __future__ import annotations

from disaster_intelligence.inference.learned import WeightsRequiredRunner

MASK2FORMER_REASON = (
    "Mask2Former is registered but disabled: official checkpoints are COCO/ADE20K instance "
    "and semantic segmentation, not Sentinel flood mapping. OpenEarthMap land-cover "
    "Mask2Former checkpoints are land cover, not flood extent. No compatible EO flood "
    "checkpoint is wired."
)


class Mask2FormerFloodRunner(WeightsRequiredRunner):
    model_id = "mask2former"
    model_version = "0"
    confidence_type = "unavailable"
    enabled = False
    disable_reason = MASK2FORMER_REASON

    def __init__(self) -> None:
        super().__init__("mask2former", reason=MASK2FORMER_REASON)
