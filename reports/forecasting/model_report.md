# Model Report

> **⚠️ ALL MODELS TRAINED ON SYNTHETIC DATA.** Performance metrics are meaningless for real-world application.  
> 3 trained models, 3 stubs (class definitions only), 1 mock ensemble.

---

## Model Architectures

| Model | Status | Parameters | Checkpoint Size | Honest Assessment |
|-------|--------|------------|-----------------|-------------------|
| Baseline MLP | ✅ Trained on synthetic | 3-layer MLP | ~94 KB | Reference baseline |
| LSTM | ✅ Trained on synthetic | 2-layer LSTM, hidden 64 | ~200 KB | Best RMSE on synthetic (~4.53) |
| Transformer | ✅ Trained on synthetic | 2-layer encoder, d_model=64 | ~2,847 KB | Comparable to LSTM on synthetic |
| PatchTST | ⚠️ STUB | Class definition only | — | No forward pass implemented |
| TimeMixer | ⚠️ STUB | Class definition only | — | No forward pass implemented |
| iTransformer | ⚠️ STUB | Class definition only | — | No forward pass implemented |
| Ensemble | ⚠️ Mock | Ridge regression wrapper | — | Not trained; predict() returns dummy |

---

## Training Details (All on Synthetic Data)

| Parameter | Value |
|-----------|-------|
| Training data | Synthetic (np.random.seed(42)) |
| Sliding window | 30 days |
| Batch size | 64 |
| Optimizer | Adam |
| Loss | MSE |
| Scheduler | ReduceLROnPlateau |
| Early stopping | Patience 10 |
| Max epochs | 100 |
| Time per epoch | ~2 seconds (synthetic, single GPU) |

---

## Performance Metrics (On Synthetic Test Set)

| Model | RMSE | MAE | R² | sMAPE | Inference Time |
|-------|------|-----|----|-------|----------------|
| MLP | 4.59 | 3.51 | 0.87 | 12.3% | 28.1ms |
| LSTM | **4.53** | **3.46** | 0.87 | 12.1% | 28.1ms |
| Transformer | 4.57 | 3.49 | 0.87 | 12.2% | 26.8ms |

**⚠️ All models show R² = 0.87 — this is suspiciously uniform and characteristic of training on synthetic data where all models converge to similar solutions because the underlying patterns are too simple.**

---

## Model Registry

Checkpoints stored at `models/checkpoints/`:
- `mlp_best.pth` — Trained on synthetic
- `lstm_best.pth` — Trained on synthetic (best)
- `transformer_best.pth` — Trained on synthetic
- `metadata.json` — Training run metadata
