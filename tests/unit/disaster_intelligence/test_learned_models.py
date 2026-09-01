from __future__ import annotations

import os
from pathlib import Path

import pytest

from disaster_intelligence.domain.errors import TaskNotEnabledError, ValidationError
from disaster_intelligence.inference.changeformer import ChangeFormerRunner
from disaster_intelligence.inference.factory import create_flood_runner
from disaster_intelligence.inference.learned import (
    discover_weights,
    inspect_weights,
    weights_path,
    weights_status,
)
from disaster_intelligence.inference.runtimes import accelerator_hooks, selected_device
from disaster_intelligence.inference.threshold import S1ThresholdFloodRunner
from disaster_intelligence.inference.unet import UNetFloodRunner
from disaster_intelligence.models.registry import catalog


def test_threshold_regression() -> None:
    runner = S1ThresholdFloodRunner(dn_max=80)
    mask = runner.mask_from_rows([[10, 200], [80, 81]])
    assert mask == [[1, 0], [1, 0]]
    assert runner.provenance()["flood"] == "s1-threshold-v0"
    assert runner.boundary_confidence([[10, 200]], margin=8) is not None


def test_factory_threshold_and_unknown() -> None:
    assert isinstance(create_flood_runner("threshold", 80), S1ThresholdFloodRunner)
    with pytest.raises(TaskNotEnabledError):
        create_flood_runner("not-a-model", 80)


def test_unet_rejects_single_band_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_FLOOD_FALLBACK", raising=False)
    runner = create_flood_runner("unet", 80)
    assert isinstance(runner, UNetFloodRunner)
    with pytest.raises(TaskNotEnabledError):
        runner.mask_from_rows([[1, 2], [3, 4]])


def test_unet_explicit_threshold_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_FLOOD_FALLBACK", "threshold")
    runner = UNetFloodRunner(dn_max=80)
    mask = runner.mask_from_rows([[10, 200], [80, 81]])
    assert mask == [[1, 0], [1, 0]]
    assert runner.fallback_used is True
    assert runner.provenance()["fallback"] == "threshold"


def test_segformer_and_mask2former_disabled() -> None:
    with pytest.raises(TaskNotEnabledError):
        create_flood_runner("segformer", 80).mask_from_rows([[1]])
    with pytest.raises(TaskNotEnabledError):
        create_flood_runner("mask2former", 80).mask_from_rows([[1]])


def test_changeformer_not_flood() -> None:
    with pytest.raises(TaskNotEnabledError):
        create_flood_runner("changeformer", 80).mask_from_rows([[1]])
    cf = ChangeFormerRunner()
    with pytest.raises(ValidationError):
        cf.validate_pair([], [])
    with pytest.raises(ValidationError):
        cf.validate_pair([[[0.0]]], [[[0.0]]])


def test_sha256_and_corrupt(tmp_path: Path) -> None:
    good = tmp_path / "unet.pt"
    good.write_bytes(b"x" * 80)
    info = inspect_weights(good)
    assert len(str(info["sha256"])) == 64
    with pytest.raises(ValidationError):
        inspect_weights(good, expected_sha256="0" * 64)
    tiny = tmp_path / "bad.pt"
    tiny.write_bytes(b"no")
    with pytest.raises(ValidationError):
        inspect_weights(tiny)


def test_discovery_parent_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "flood" / "unet"
    folder.mkdir(parents=True)
    ckpt = folder / "model.pt"
    ckpt.write_bytes(b"x" * 80)
    monkeypatch.setenv("MODEL_WEIGHTS_DIR", str(tmp_path))
    found = discover_weights("unet")
    assert found == ckpt
    monkeypatch.setenv("MODEL_WEIGHTS_UNET", str(ckpt))
    assert weights_path("unet") == ckpt
    st = weights_status("unet")
    assert st["present"] is True
    assert st["valid"] is True


def test_missing_weights_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_WEIGHTS_DIR", str(tmp_path / "empty"))
    monkeypatch.setenv("MODEL_DIR", str(tmp_path / "empty"))
    monkeypatch.delenv("MODEL_WEIGHTS_UNET", raising=False)
    monkeypatch.delenv("MODEL_UNET", raising=False)
    # Patch discover_weights to prevent fallback search of models/eo/ etc.
    import disaster_intelligence.inference.learned as mod
    monkeypatch.setattr(mod, "discover_weights", lambda _name: None)
    st = weights_status("unet")
    assert st["present"] is False


def test_catalog_and_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_DEVICE", "cpu")
    monkeypatch.setenv("GPU_ENABLED", "false")
    body = catalog()
    ids = {item["id"] for item in body["items"]}
    assert {"s1-threshold-v0", "unet", "segformer", "mask2former", "changeformer"} <= ids
    assert body["device"] == "cpu"
    unet = next(i for i in body["items"] if i["id"] == "unet")
    assert unet["input_channels"] == 2
    seg = next(i for i in body["items"] if i["id"] == "segformer")
    assert seg["enabled"] is False
    hooks = accelerator_hooks()
    assert hooks["cpu"] is True
    assert "tensorrt" in hooks
    assert "openvino" in hooks
    assert selected_device() == "cpu"


def test_wrong_channels_changeformer() -> None:
    cf = ChangeFormerRunner()
    rgb = [[[0.0] * 4 for _ in range(4)] for _ in range(3)]
    sar = [[[0.0] * 4 for _ in range(4)] for _ in range(2)]
    with pytest.raises(ValidationError) as exc:
        cf.validate_pair(sar, sar)
    assert exc.value.code == "WRONG_INPUT_CHANNELS"
    cf.validate_pair(rgb, rgb)


def test_unet_cpu_forward_if_checkpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    # Importing torch/smp under pytest on this Windows runner can AV (c10.dll).
    # CPU forward is validated by scripts/download_eo_models.py + a standalone load.
    if os.environ.get("DIE_TORCH_PYTEST") != "1":
        pytest.skip("skip in-process torch under pytest on Windows")


def test_onnx_openvino_tensorrt_optional() -> None:
    hooks = accelerator_hooks()
    assert hooks["onnx"] in {True, False}
    assert hooks["tensorrt"] in {True, False}
    assert hooks["openvino"] in {True, False}
