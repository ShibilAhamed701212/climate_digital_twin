from __future__ import annotations

from disaster_intelligence.inference.learned import WeightsRequiredRunner

SEGFORMER_REASON = (
    "SegFormer is registered but disabled: no compatible pretrained Sentinel-1/Sentinel-2 "
    "flood checkpoint was found. Official NVIDIA SegFormer weights are ADE20K/Cityscapes. "
    "IBM-NASA Prithvi Sen1Floods11 is a different architecture (not SegFormer). "
    "Do not use ADE20K/ImageNet checkpoints as flood models."
)


class SegFormerFloodRunner(WeightsRequiredRunner):
    model_id = "segformer"
    model_version = "0"
    confidence_type = "unavailable"
    enabled = False
    disable_reason = SEGFORMER_REASON

    def __init__(self) -> None:
        super().__init__("segformer", reason=SEGFORMER_REASON)
