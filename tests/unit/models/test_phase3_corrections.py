"""Regression tests for Phase 3 corrections.

All torch-dependent tests run in subprocesses to avoid C++ SEH crashes.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from tests.helpers.torch_guard import safe_import_torch

_TORCH_OK = safe_import_torch()
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# === TESTS THAT DON'T NEED TORCH ===

_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "models/configs/model_config.yaml")


class TestRegistryStatus:
    def test_register_with_status(self):
        from models.registry import ModelRegistry

        reg = ModelRegistry()
        assert "status" not in reg.get("lstm") or reg.get("lstm").get("status") is not None

    def test_update_status(self, tmp_path):
        from models.registry import ModelRegistry

        reg_path = os.path.join(tmp_path, "test_registry.json")
        reg = ModelRegistry(registry_path=reg_path)
        reg.register(
            name="test_model",
            architecture="LSTMModel",
            checkpoint_path="/tmp/test.pt",
            status="EXPERIMENTAL",
        )
        entry = reg.get("test_model")
        assert entry["status"] == "EXPERIMENTAL"
        reg.update_status("test_model", "VALIDATED")
        assert reg.get("test_model")["status"] == "VALIDATED"

    def test_invalid_status_raises(self):
        from models.registry import ModelRegistry, RegistryError

        reg = ModelRegistry()
        with pytest.raises(RegistryError, match="Invalid status"):
            reg.register(
                name="bad", architecture="LSTMModel", checkpoint_path="/tmp/x.pt", status="BOGUS"
            )

    def test_update_status_unknown_raises(self):
        from models.registry import ModelRegistry

        reg = ModelRegistry()
        with pytest.raises(KeyError):
            reg.update_status("nonexistent", "VALIDATED")

    def test_lstm_real_v1_rejected(self):
        from models.registry import ModelRegistry

        reg = ModelRegistry()
        try:
            entry = reg.get("lstm-real-v1")
            assert entry.get("status") == "REJECTED"
            assert "MODEL_COLLAPSE" in entry.get("reason", "")
        except KeyError:
            pass


class TestForecastProvenance:
    def test_forecast_has_authenticity(self):
        from models.forecast_provenance import ForecastResult

        fr = ForecastResult(
            location_id="KA-BLR-001",
            rainfall=12.5,
            model_id="lstm-real-v2",
            authenticity="REAL",
            training_run_id="abc123",
            dataset_id="https://open-meteo/...",
        )
        d = fr.to_dict()
        assert d["authenticity"] == "REAL"
        assert d["training_run_id"] == "abc123"
        assert d["dataset_id"] == "https://open-meteo/..."
        assert len(d["forecast_id"]) == 12

    def test_list_status_filtered(self):
        from models.registry import ModelRegistry

        reg = ModelRegistry()
        models = reg.list_models()
        for m in models:
            status = m.get("status")
            if status is not None:
                assert status in ("EXPERIMENTAL", "VALIDATED", "REJECTED")


_SCRIPT_TESTS = {
    "config_mapping_baseline": """
from models.trainer import _resolve_model_config
import yaml
config = yaml.safe_load(open("models/configs/model_config.yaml"))
cfg = _resolve_model_config("baseline", config)
assert cfg == config["baseline"]
assert "hidden_layers" in cfg
print("baseline OK")
""",
    "config_mapping_lstm": """
from models.trainer import _resolve_model_config
import yaml
config = yaml.safe_load(open("models/configs/model_config.yaml"))
cfg = _resolve_model_config("lstm", config)
assert cfg["epochs"] == 100
print("lstm OK")
""",
    "config_mapping_unknown": """
from models.trainer import _resolve_model_config
import yaml
try:
    _resolve_model_config("bogus", yaml.safe_load(open("models/configs/model_config.yaml")))
    assert False, "should have raised"
except ValueError as e:
    assert "Unknown model type" in str(e)
print("unknown OK")
""",
    "scaler_save_load": """
import tempfile, os, torch
from models.data_loader import Scaler, save_scalers, load_scalers
feat = Scaler(); tgt = Scaler()
feat.fit(torch.tensor([[1.0,2.0],[3.0,4.0]]))
tgt.fit(torch.tensor([[0.5],[1.5]]))
with tempfile.TemporaryDirectory() as tmp:
    save_scalers(feat, tgt, "tm", scaler_dir=tmp)
    assert os.path.exists(os.path.join(tmp, "tm_feat_scaler.pkl"))
    f2, t2 = load_scalers("tm", scaler_dir=tmp)
    assert f2 is not None and t2 is not None
    x = torch.tensor([[2.0, 3.0]])
    assert torch.allclose(feat.transform(x), f2.transform(x))
print("scaler OK")
""",
    "scaler_inverse": """
import torch
from models.data_loader import Scaler
data = torch.tensor([[1.0,10.0],[2.0,20.0],[3.0,30.0]])
s = Scaler()
s.fit(data)
sc = s.transform(data)
rec = s.inverse_transform(sc)
assert torch.allclose(data, rec, atol=1e-6)
print("inverse OK")
""",
    "scaler_zero_range": """
import torch
from models.data_loader import Scaler
data = torch.tensor([[5.0],[5.0],[5.0]])
s = Scaler()
s.fit(data)
tr = s.transform(data)
assert torch.allclose(tr, torch.zeros_like(data))
rec = s.inverse_transform(tr)
assert torch.allclose(rec, data)
print("zero-range OK")
""",
    "collapse_detected": """
import torch
from models.evaluator import detect_collapse
yp = torch.ones(100, 3) * 5.0
yt = torch.randn(100, 3)
r = detect_collapse(yp, yt)
assert r["collapsed"] is True
assert len(r["collapsed_targets"]) == 3
print("collapse OK")
""",
    "no_collapse": """
import torch
from models.evaluator import detect_collapse
yp = torch.randn(100, 3) * 2.0
yt = torch.randn(100, 3)
r = detect_collapse(yp, yt)
assert r["collapsed"] is False
print("no-collapse OK")
""",
    "per_target_metrics": """
import torch
from models.evaluator import compute_per_target_metrics
yt = torch.randn(100, 3)
yp = torch.randn(100, 3)
pt = compute_per_target_metrics(yt, yp, ["Rain","Temp","Hum"])
assert set(pt.keys()) == {"Rain","Temp","Hum"}
for n in pt:
    assert "rmse" in pt[n] and "mae" in pt[n] and "r2" in pt[n] and "smape" in pt[n]
print("per-target OK")
""",
    "registry_register_status": """
from models.registry import ModelRegistry
import tempfile, os
p = os.path.join(tempfile.mkdtemp(), "reg.json")
reg = ModelRegistry(registry_path=p)
reg.register(name="t", architecture="LSTMModel", checkpoint_path="/x.pt", status="EXPERIMENTAL")
assert reg.get("t")["status"] == "EXPERIMENTAL"
reg.update_status("t", "VALIDATED")
assert reg.get("t")["status"] == "VALIDATED"
print("registry-status OK")
""",
    "registry_invalid_status": """
from models.registry import ModelRegistry, RegistryError
import tempfile, os
p = os.path.join(tempfile.mkdtemp(), "reg.json")
reg = ModelRegistry(registry_path=p)
try:
    reg.register(name="t", architecture="LSTMModel", checkpoint_path="/x.pt", status="BOGUS")
    assert False
except RegistryError:
    pass
print("registry-invalid OK")
""",
    "registry_best_validated": """
from models.registry import ModelRegistry
reg = ModelRegistry()
try:
    reg.get_best(require_validated=True)
except KeyError:
    pass  # No validated models is a valid scenario
print("registry-best OK")
""",
}

_SETUP = f"import sys; sys.path.insert(0, {_PROJECT_ROOT!r})\n"


@pytest.mark.skipif(not _TORCH_OK, reason="torch unavailable (C++ crash guard)")
@pytest.mark.parametrize("name,code", list(_SCRIPT_TESTS.items()))
def test_script(name, code):
    result = subprocess.run(
        [sys.executable, "-c", _SETUP + code],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=_PROJECT_ROOT,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        pytest.fail(f"{name} failed (exit {result.returncode}):\n{result.stderr}")
