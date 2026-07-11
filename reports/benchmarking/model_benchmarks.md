# Model Benchmarks

> **⚠️ All benchmarks on synthetic data.** Not representative of real-world performance.

---

## Prediction Performance (Synthetic Test Set)

| Model | RMSE ↓ | MAE ↓ | R² ↑ | sMAPE ↓ | Notes |
|-------|--------|-------|------|---------|-------|
| Baseline MLP | 4.59 | 3.51 | 0.87 | 12.3% | Reference baseline |
| LSTM | **4.53** | **3.46** | 0.87 | 12.1% | Best on synthetic |
| Transformer | 4.57 | 3.49 | 0.87 | 12.2% | Comparable to LSTM |
| PatchTST | — | — | — | — | ⚠️ Stub — not trained |
| TimeMixer | — | — | — | — | ⚠️ Stub — not trained |
| iTransformer | — | — | — | — | ⚠️ Stub — not trained |
| Ensemble | — | — | — | — | ⚠️ Mock — not trained |

---

## Inference Latency (CPU, Single Sample)

| Model | Total | Per Sample | Model Load |
|-------|-------|------------|------------|
| MLP | 28.1ms | 0.9ms | ~100ms |
| LSTM | 28.1ms | 0.9ms | ~150ms |
| Transformer | **26.8ms** | **0.8ms** | ~500ms |

---

## Checkpoint Sizes

| Model | Size | Parameters |
|-------|------|------------|
| MLP | 94 KB | ~30K |
| LSTM | 200 KB | ~80K |
| Transformer | 2,847 KB | ~500K |

---

## Honesty Note

The uniform R²=0.87 across all models is a red flag. On real data, different architectures would produce meaningfully different results. The synthetic data likely contains simple linear patterns that any model with sufficient capacity can learn equally well. **These benchmarks should not be used to make claims about real-world forecasting accuracy.**
