from __future__ import annotations

from pathlib import Path

import yaml


def test_disaster_engine_is_optional_profile() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    service = compose["services"]["disaster-engine"]
    assert service["profiles"] == ["disaster"]
    assert "8008" in str(service["ports"])
    assert "127.0.0.1" in str(service["ports"])
    core = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    for name, svc in core["services"].items():
        if name == "disaster-engine":
            continue
        deps = svc.get("depends_on") or {}
        if isinstance(deps, dict):
            assert "disaster-engine" not in deps
        else:
            assert "disaster-engine" not in list(deps)


def test_prod_overlay_hardens_disaster_engine() -> None:
    prod = yaml.safe_load(Path("docker-compose.prod.yml").read_text(encoding="utf-8"))
    die = prod["services"]["disaster-engine"]
    assert die["read_only"] is True
    assert "no-new-privileges:true" in die["security_opt"]


def test_gpu_overlay_enables_cuda_flags() -> None:
    text = Path("docker-compose.gpu.yml").read_text(encoding="utf-8")
    assert "GPU_ENABLED=true" in text
    assert "capabilities: [gpu]" in text


def test_rag_dockerfile_pins_cpu_torch() -> None:
    text = Path("deployment/docker/Dockerfile.rag").read_text(encoding="utf-8")
    assert "download.pytorch.org/whl/cpu" in text


def test_compose_passes_earth_observation_credentials() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    env = "\n".join(compose["services"]["disaster-engine"]["environment"])
    assert "EARTHDATA_USERNAME" in env
    assert "STAC_PROVIDER" in env
    assert "HOST_MODEL_WEIGHTS_DIR" in str(compose["services"]["disaster-engine"]["volumes"])
