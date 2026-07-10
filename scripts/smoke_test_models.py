"""Smoke test every trained model: load, inference, batch, API.

Tests:
  - Baseline, LSTM, Transformer (have checkpoints)
  - PatchTST, TimeMixer, iTransformer (new architecture stubs)
  - Ensemble meta-learner
  - Registry
  - Scaler loading
"""

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
import yaml

CONFIG_PATH = "models/configs/model_config.yaml"
CHECKPOINT_DIR = Path("models/checkpoints")
EXPORTED_DIR = Path("models/exported")

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

n_features = len(config["data"]["feature_columns"])
n_targets = len(config["data"]["target_columns"])
seq_len = config["data"]["sequence_length"]
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

results = []


def test(name: str, model, input_tensor=None):
    passed = True
    errors = []
    latency = 0.0

    try:
        if input_tensor is None:
            input_tensor = torch.randn(4, seq_len, n_features)
        model.eval()
        model.to(device)
        input_tensor = input_tensor.to(device)

        # Single inference
        start = time.perf_counter()
        with torch.no_grad():
            out = model(input_tensor[:1])
        latency = (time.perf_counter() - start) * 1000
        assert out.shape[0] == 1, f"Expected batch=1, got {out.shape[0]}"
        assert out.shape[1] == n_targets, f"Expected {n_targets} targets, got {out.shape[1]}"

        # Batch inference
        start = time.perf_counter()
        with torch.no_grad():
            out_batch = model(input_tensor)
        batch_latency = (time.perf_counter() - start) * 1000
        assert out_batch.shape[0] == 4, f"Expected batch=4, got {out_batch.shape[0]}"

        errors.append(f"inf={latency:.1f}ms")
        errors.append(f"batch={batch_latency:.1f}ms")
    except Exception as e:
        passed = False
        errors.append(str(e))

    status = "PASS" if passed else "FAIL"
    results.append(
        {"name": name, "status": status, "latency_ms": latency, "details": "; ".join(errors)}
    )
    print(f"  [{status}] {name:30s} {' | '.join(errors)}")


def load_checkpoint(model_cls, ckpt_path):
    model = model_cls(n_features=n_features, n_targets=n_targets)
    sd = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(sd)
    return model


# ── 1. Baseline ──────────────────────────────────────────────
print("\n--- Baseline ---")
ckpt = CHECKPOINT_DIR / "baseline_best.pt"
if ckpt.exists():
    from models.baseline.model import BaselineModel

    m = load_checkpoint(BaselineModel, ckpt)
    test("Baseline", m)
else:
    print("  [SKIP] checkpoint not found")

# ── 2. LSTM ──────────────────────────────────────────────────
print("\n--- LSTM ---")
ckpt = CHECKPOINT_DIR / "lstm_best.pt"
if ckpt.exists():
    from models.lstm.model import LSTMModel

    m = load_checkpoint(LSTMModel, ckpt)
    test("LSTM", m)
else:
    print("  [SKIP] checkpoint not found")

# ── 3. Transformer ──────────────────────────────────────────
print("\n--- Transformer ---")
ckpt = CHECKPOINT_DIR / "transformer_best.pt"
if ckpt.exists():
    from models.transformer.model import TransformerModel

    m = load_checkpoint(TransformerModel, ckpt)
    test("Transformer", m)
else:
    print("  [SKIP] checkpoint not found")

# ── 4. PatchTST ─────────────────────────────────────────────
print("\n--- PatchTST ---")
try:
    from models.patchtst.model import PatchTSTModel

    m = PatchTSTModel(n_features=n_features, n_targets=n_targets)
    test("PatchTST (untrained)", m)
except Exception as e:
    print(f"  [FAIL] {e}")

# ── 5. TimeMixer ────────────────────────────────────────────
print("\n--- TimeMixer ---")
try:
    from models.timemixer.model import TimeMixerModel

    m = TimeMixerModel(n_features=n_features, n_targets=n_targets)
    test("TimeMixer (untrained)", m)
except Exception as e:
    print(f"  [FAIL] {e}")

# ── 6. iTransformer ─────────────────────────────────────────
print("\n--- iTransformer ---")
try:
    from models.itransformer.model import ITransformerModel

    m = ITransformerModel(n_features=n_features, n_targets=n_targets)
    test("iTransformer (untrained)", m)
except Exception as e:
    print(f"  [FAIL] {e}")

# ── 7. Ensemble Meta-Learner ────────────────────────────────
print("\n--- Ensemble Meta-Learner ---")
try:
    from models.ensemble.meta_learner import EnsembleMetaLearner

    em = EnsembleMetaLearner()
    dummy_preds = {
        "model_a": np.random.randn(10, n_targets),
        "model_b": np.random.randn(10, n_targets),
    }
    dummy_targets = np.random.randn(10, n_targets)
    em.fit(dummy_preds, dummy_targets)
    out = em.predict(dummy_preds)
    print(f"  [PASS] Ensemble fit+pred OK, shape={out.shape}")
except Exception as e:
    print(f"  [FAIL] {e}")

# ── 8. Registry ─────────────────────────────────────────────
print("\n--- ModelRegistry ---")
try:
    from models.registry import ModelRegistry

    reg = ModelRegistry()
    registered = reg.list_models()
    print(f"  Registered models: {registered}")
    for name in registered:
        info = reg.get_model_info(name)
        print(f"    {name}: {info.get('architecture', '?')}")
except Exception as e:
    print(f"  [FAIL] Registry: {e}")

# ── 9. Scaler + Predictor ───────────────────────────────────
print("\n--- Scaler + Predict(pipeline) ---")
try:
    from models.data_loader import Scaler

    s = Scaler()
    s.fit(torch.randn(100, n_targets))
    print("  [PASS] Scaler fit OK")
    inv = s.inverse_transform(torch.randn(4, n_targets))
    print(f"  [PASS] Scaler inverse OK, shape={inv.shape}")
except Exception as e:
    print(f"  [FAIL] Scaler: {e}")

# ── Summary ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("MODEL SMOKE TEST SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
for r in results:
    print(f"  [{r['status']}] {r['name']:30s} {r['details']}")
print(f"\n  {passed}/{len(results)} passed")
