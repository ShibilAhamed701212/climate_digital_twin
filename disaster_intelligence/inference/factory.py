from __future__ import annotations

from disaster_intelligence.domain.errors import TaskNotEnabledError
from disaster_intelligence.inference.changeformer import ChangeFormerFloodRunner
from disaster_intelligence.inference.learned import WeightsRequiredRunner
from disaster_intelligence.inference.mask2former import Mask2FormerFloodRunner
from disaster_intelligence.inference.runtimes import flood_fallback_to_threshold
from disaster_intelligence.inference.segformer import SegFormerFloodRunner
from disaster_intelligence.inference.threshold import S1ThresholdFloodRunner
from disaster_intelligence.inference.unet import UNetFloodRunner

ENABLED_FLOOD_MODELS = {"threshold", "s1-threshold-v0", "s1-threshold"}
LEARNED_MODELS = {"unet", "segformer", "mask2former", "changeformer"}


def create_flood_runner(
    model: str, dn_max: int
) -> S1ThresholdFloodRunner | WeightsRequiredRunner | UNetFloodRunner:
    name = (model or "threshold").strip().lower()
    if name in ENABLED_FLOOD_MODELS:
        return S1ThresholdFloodRunner(dn_max=dn_max)
    if name == "unet":
        return UNetFloodRunner(dn_max=dn_max)
    if name == "segformer":
        if flood_fallback_to_threshold():
            runner = S1ThresholdFloodRunner(dn_max=dn_max, requested=name)
            runner.fallback_used = True
            return runner
        return SegFormerFloodRunner()
    if name == "mask2former":
        if flood_fallback_to_threshold():
            runner = S1ThresholdFloodRunner(dn_max=dn_max, requested=name)
            runner.fallback_used = True
            return runner
        return Mask2FormerFloodRunner()
    if name == "changeformer":
        return ChangeFormerFloodRunner()
    raise TaskNotEnabledError(f"MODEL_FLOOD={model} is not enabled")
