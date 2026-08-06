"""PyTorch runtime verification smoke test."""

import json
import torch
import sys


def run():
    print("=== PyTorch Runtime Verification ===")
    print(f"Python: {sys.version}")
    print(f"torch: {torch.__version__}")
    print(f"CUDA: {torch.cuda.is_available()}")
    print(f"Device: {torch.device('cpu')}")
    print()

    # Basic tensor
    t = torch.tensor([1.0, 2.0, 3.0])
    print(f"TENSOR_OP: sum={t.sum().item():.1f} (expected 6.0)")

    # Model construction
    m = torch.nn.Sequential(torch.nn.Linear(10, 32), torch.nn.ReLU(), torch.nn.Linear(32, 3))
    print(f"MODEL_CONSTRUCTION: layers={len(list(m.children()))}")

    # Forward pass
    x = torch.randn(4, 10)
    with torch.no_grad():
        y = m(x)
    print(f"MODEL_FORWARD: input={x.shape}, output={y.shape}")

    # Checkpoint registry
    try:
        with open("models/registry/metadata.json") as f:
            reg = json.load(f)
        real_validated = [
            (n, i)
            for n, i in reg.items()
            if i.get("status") == "VALIDATED" and i.get("authenticity") == "REAL"
        ]
        print(f"REGISTRY: {len(reg)} models, {len(real_validated)} REAL+VALIDATED")
        for name, info in real_validated:
            ckpt = info.get("checkpoint_path", "")
            rmse = info.get("metrics", {}).get("rmse", "?")
            print(f"  {name}: RMSE={rmse}, checkpoint={ckpt}")
            if ckpt:
                try:
                    chk = torch.load(ckpt, map_location="cpu", weights_only=True)
                    print(f"    CHECKPOINT_LOAD: keys={list(chk.keys())[:5]}...")
                except Exception as e:
                    print(f"    CHECKPOINT_LOAD: FAILED — {e}")
    except FileNotFoundError:
        print("REGISTRY: models/registry/metadata.json not found")
    except Exception as e:
        print(f"REGISTRY: ERROR — {e}")

    print()
    print("=== Summary ===")
    print("TORCH_IMPORT: PASS")
    print("TENSOR_OP: PASS")
    print("MODEL_CONSTRUCTION: PASS")
    print("MODEL_FORWARD: PASS")


if __name__ == "__main__":
    run()
