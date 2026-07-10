"""Register trained model checkpoints in the ModelRegistry."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.registry import ModelRegistry

CHECKPOINT_DIR = Path("models/checkpoints")
MODEL_CONFIG = {
    "baseline": {"architecture": "BaselineModel", "metrics": {"rmse": 4.59, "r2": 0.87}},
    "lstm": {"architecture": "LSTMModel", "metrics": {"rmse": 4.53, "r2": 0.87}},
    "transformer": {"architecture": "TransformerModel", "metrics": {"rmse": 4.57, "r2": 0.87}},
    "patchtst": {"architecture": "PatchTSTModel", "metrics": {}},
    "timemixer": {"architecture": "TimeMixerModel", "metrics": {}},
    "itransformer": {"architecture": "ITransformerModel", "metrics": {}},
}

reg = ModelRegistry()

for model_name, info in MODEL_CONFIG.items():
    ckpt_path = CHECKPOINT_DIR / f"{model_name}_best.pt"
    if ckpt_path.exists():
        entry = reg.register(
            name=model_name,
            architecture=info["architecture"],
            checkpoint_path=str(ckpt_path),
            metrics=info["metrics"],
        )
        print(f"  Registered: {model_name} ({info['architecture']})")
    else:
        print(f"  Skipped: {model_name} (no checkpoint)")

print(f"\nTotal registered: {reg.count()}")
for m in reg.list_models():
    print(f"  {m['name']:20s} {m['architecture']:25s} ckpt={m['checkpoint_path']}")
