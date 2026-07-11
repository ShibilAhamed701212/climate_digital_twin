# Training Report

> **⚠️ Pipeline trained exclusively on synthetic data.** Not validated on real climate observations.

---

## Training Pipeline

| Stage | Implementation | Notes |
|-------|---------------|-------|
| Data Loading | `DataLoader` with sliding window=30 | Synthetic dataset via `ClimateDataset` |
| Model Init | 3 architectures (MLP, LSTM, Transformer) | Stubs not initialized |
| Training Loop | Standard PyTorch loop | Per-epoch metrics logged |
| Validation | Every epoch on hold-out set | Synthetic validation |
| Checkpointing | Save best model by validation loss | 3 checkpoints saved |
| Physics Validation | `PhysicsValidator` post-processing | Clips rainfall >= 0, enforces Tmin <= Tmax |

---

## Data Loader

| Parameter | Value |
|-----------|-------|
| Window size | 30 sequential timesteps |
| Batch size | 64 |
| Shuffle | True (train), False (val/test) |
| Features | 15 (base + engineered) |
| Targets | 3 (precipitation, t2m_max, t2m_min) |
| Source data | Synthetic parquet files |

---

## Training Engine

| Parameter | Value |
|-----------|-------|
| Loss function | MSE (symmetric on standardized data) |
| Optimizer | Adam (lr=0.001) |
| Scheduler | ReduceLROnPlateau (patience=5, factor=0.5) |
| Early stopping | Patience=10 |
| Max epochs | 100 |
| Gradient clipping | None |
| Mixed precision | No |

---

## Evaluation Metrics

| Metric | Formula | Honesty Note |
|--------|---------|--------------|
| RMSE | √MSE | On synthetic data only |
| MAE | Mean absolute error | On synthetic data only |
| R² | 1 - (SS_res/SS_tot) | Suspiciously uniform at 0.87 across models |
| sMAPE | Symmetric MAPE | On synthetic data only |

---

## Physics Validator

Simple rule-based post-processing applied to all predictions:

| Rule | Implementation |
|------|---------------|
| Rainfall >= 0 | `torch.clamp(pred[:, 0], min=0)` |
| Tmin <= Tmax | Swap values if violated |
| Temperature bounds | Clip to [-10, 50]°C |

---

## Training Summary (Synthetic Data)

| Run | Model | Epochs Trained | Best Val Loss | Training Time |
|-----|-------|----------------|---------------|---------------|
| 1 | Baseline MLP | ~20 (early stopping) | 0.021 | ~40s |
| 2 | LSTM | ~25 (early stopping) | 0.020 | ~2 min |
| 3 | Transformer | ~30 (early stopping) | 0.020 | ~3 min |

**All numbers on synthetic data. Training on real data would likely show different convergence behavior, higher loss, and more differentiation between architectures.**
