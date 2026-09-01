from __future__ import annotations

import importlib.util

from disaster_intelligence.config import env_flag, env_str


def _spec_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def selected_device() -> str:
    """Pick a device without importing torch (Windows pytest can crash on torch DLL load)."""
    requested = env_str("MODEL_DEVICE", "auto").strip().lower() or "auto"
    cuda_ok = env_flag("GPU_ENABLED", False)
    if requested in {"cpu"}:
        return "cpu"
    if requested in {"cuda", "gpu"}:
        return "cuda" if cuda_ok else "cpu"
    if requested == "tensorrt":
        if accelerator_hooks()["tensorrt"] and cuda_ok:
            return "tensorrt"
        return "cuda" if cuda_ok else "cpu"
    if requested == "openvino":
        return "openvino" if accelerator_hooks()["openvino"] else "cpu"
    if cuda_ok:
        return "cuda"
    return "cpu"


def selected_runtime() -> str:
    requested = env_str("MODEL_RUNTIME", "auto").strip().lower() or "auto"
    hooks = accelerator_hooks()
    device = selected_device()
    if requested == "tensorrt":
        return "tensorrt" if hooks["tensorrt"] else ("onnx" if hooks["onnx"] else "torch")
    if requested == "openvino":
        return "openvino" if hooks["openvino"] else "torch"
    if requested == "onnx":
        return "onnx" if hooks["onnx"] else "torch"
    if requested in {"torch", "pytorch"}:
        return "torch"
    if requested == "numpy":
        return "numpy"
    if device == "tensorrt" and hooks["tensorrt"]:
        return "tensorrt"
    if device == "openvino" and hooks["openvino"]:
        return "openvino"
    if hooks["torch"]:
        return "torch"
    if hooks["onnx"]:
        return "onnx"
    return "numpy"


def accelerator_hooks() -> dict[str, bool]:
    torch_ok = _spec_available("torch")
    onnx = _spec_available("onnxruntime") or _spec_available("onnxruntime_gpu")
    tensorrt = _spec_available("tensorrt") or _spec_available("torch_tensorrt")
    openvino = _spec_available("openvino")
    gpu = env_flag("GPU_ENABLED", False)
    return {
        "cpu": True,
        "cuda": gpu,
        "onnx": onnx,
        "torch": torch_ok,
        "tensorrt": tensorrt,
        "openvino": openvino,
        "inference_enabled": torch_ok or onnx,
    }


def flood_fallback_to_threshold() -> bool:
    return env_str("MODEL_FLOOD_FALLBACK", "none").strip().lower() == "threshold"


def oom_fallback_to_cpu() -> bool:
    return env_str("MODEL_OOM_FALLBACK", "none").strip().lower() == "cpu"


def vram_batch_size() -> int:
    raw = env_str("MODEL_BATCH_SIZE", "1").strip()
    try:
        return max(1, min(int(raw), 4))
    except ValueError:
        return 1


def tile_size() -> int:
    raw = env_str("MODEL_TILE_SIZE", "512").strip()
    try:
        return max(64, min(int(raw), 1024))
    except ValueError:
        return 512
