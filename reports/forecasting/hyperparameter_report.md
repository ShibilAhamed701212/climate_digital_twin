# Hyperparameter Report

> **⚠️ No hyperparameter optimization performed.** Values below are initial choices that produced reasonable convergence on synthetic data. Real data would likely require different settings.

---

## Data Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Window size | 30 | Arbitrary choice |
| Train/val/test split | 70/15/15 | Temporal split on synthetic timestamps |
| Batch size | 64 | Power of 2 for GPU alignment (CPU fallback) |
| Features | 15 | Base + engineered |
| Targets | 3 | precipitation, t2m_max, t2m_min |
| Standardization | Z-score (fit on train) | Fitted to synthetic distribution |

---

## Training Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Epochs | 100 (max, with early stopping) | Early stopping at ~20–30 on synthetic |
| Optimizer | Adam | Default β₁=0.9, β₂=0.999 |
| Learning rate | 0.001 | Standard Adam default |
| LR scheduler | ReduceLROnPlateau | patience=5, factor=0.5 |
| Early stopping patience | 10 | Triggers on synthetic validation loss plateau |
| Loss function | MSE | Standard for regression |
| Gradient clipping | None | Not needed on synthetic |

---

## Per-Model Hyperparameters

### Baseline MLP
| Parameter | Value |
|-----------|-------|
| Hidden layers | [128, 64, 32] |
| Activation | ReLU |
| Dropout | 0.2 |
| Input size | 15 features × 30 timesteps |
| Output size | 3 targets × 30 timesteps |

### LSTM
| Parameter | Value |
|-----------|-------|
| Hidden size | 64 |
| Num layers | 2 |
| Dropout | 0.2 (between layers) |
| Bidirectional | False |
| Input size | 15 features |

### Transformer
| Parameter | Value |
|-----------|-------|
| d_model | 64 |
| Nhead | 4 |
| Num encoder layers | 2 |
| Dim feedforward | 256 |
| Dropout | 0.1 |

### PatchTST (Stub)
| Parameter | Value | Notes |
|-----------|-------|-------|
| Any | — | ⚠️ Class definition only. Not instantiable. |

### TimeMixer (Stub)
| Parameter | Value | Notes |
|-----------|-------|-------|
| Any | — | ⚠️ Class definition only. Not instantiable. |

### iTransformer (Stub)
| Parameter | Value | Notes |
|-----------|-------|-------|
| Any | — | ⚠️ Class definition only. Not instantiable. |

### Ensemble
| Parameter | Value | Notes |
|-----------|-------|-------|
| Meta-learner | Ridge regression | ⚠️ Not trained on base model outputs |
| Base models | MLP, LSTM, Transformer | ⚠️ Ensemble weights are placeholder |

---

## Export Parameters

| Parameter | Value |
|-----------|-------|
| Checkpoint format | PyTorch `.pth` (state_dict only) |
| Checkpoint dir | `models/checkpoints/` |
| Save metric | Best validation loss |
| Max saves | 1 per model (overwritten) |

---

## Note on Hyperparameter Selection

No grid search, random search, or Bayesian optimization was performed. All hyperparameters are initial values from literature defaults (LSTM: 2 layers, hidden 64; Transformer: d_model=64). The suspiciously uniform R²=0.87 across all models suggests the synthetic data is too simple to differentiate model capacity. Real data would likely require architectural tuning.
