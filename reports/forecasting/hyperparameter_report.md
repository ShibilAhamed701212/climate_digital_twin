# Hyperparameter Report — Climate Digital Twin

## Overview

Hyperparameters are defined in `models/configs/model_config.yaml`. The configuration covers data loading, training, evaluation, and export.

---

## Data Hyperparameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `sequence_length` | **30** | Number of past timesteps used for forecasting (30 days) |
| `batch_size` | **64** | Number of sequences per training batch |
| `feature_columns` | 11 columns | Input features for the model |
| `target_columns` | 3 columns | Output variables to predict |

### Feature Columns

1. `Rainfall`
2. `MaxTemp`
3. `MinTemp`
4. `Month`
5. `Week`
6. `Season`
7. `Monsoon`
8. `RollingRain7`
9. `RollingRain30`
10. `RollingTemp7`
11. `RollingTemp30`

### Target Columns

1. `Rainfall`
2. `MaxTemp`
3. `MinTemp`

---

## Training Hyperparameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `device` | `auto` | Auto-selects CUDA if available, else CPU |
| `loss` | `mse` | Mean Squared Error loss function |
| `optimizer` | `adam` | Adam optimizer |
| `early_stopping_patience` | **10** | Epochs without improvement before stopping |
| `validation_frequency` | **1** | Validate every epoch |
| `random_seed` | **42** | Random seed for reproducibility |

---

## Per-Model Hyperparameters

### Baseline

| Parameter | Value |
|-----------|-------|
| `hidden_layers` | **[64, 32]** |
| `learning_rate` | **0.001** |
| `epochs` | **50** |
| `dropout` | 0.1 (default in code) |

**Architecture:** `Linear(330, 64) → ReLU → Dropout → Linear(64, 32) → ReLU → Dropout → Linear(32, 3)`

### LSTM

| Parameter | Value |
|-----------|-------|
| `hidden_dim` | **128** |
| `num_layers` | **2** |
| `dropout` | **0.2** |
| `learning_rate` | **0.001** |
| `epochs` | **100** |
| `bidirectional` | **false** |

**Architecture:** 2-layer LSTM(11→128) → Linear(128→3)

### Transformer

| Parameter | Value |
|-----------|-------|
| `d_model` | **128** |
| `nhead` | **4** |
| `num_encoder_layers` | **3** |
| `dim_feedforward` | **512** |
| `dropout` | **0.1** |
| `learning_rate` | **0.0005** |
| `epochs` | **100** |
| `max_len` | 1000 (default) |

**Architecture:** Linear(11→128) → PosEncoding → 3× TransformerEncoderLayer(4-head, d_model=128, FF=512) → Linear(128→3)

---

## Stub Model Hyperparameters (Untrained)

These models have architecture defaults in their source code but no training config:

### PatchTST

| Parameter | Default Value |
|-----------|--------------|
| `patch_len` | 8 |
| `d_model` | 128 |
| `nhead` | 4 |
| `num_encoder_layers` | 3 |
| `dim_feedforward` | 512 |
| `dropout` | 0.1 |

### TimeMixer

| Parameter | Default Value |
|-----------|--------------|
| `d_model` | 128 |
| `num_layers` | 3 |
| `dropout` | 0.1 |

### iTransformer

| Parameter | Default Value |
|-----------|--------------|
| `d_model` | 128 |
| `nhead` | 4 |
| `num_encoder_layers` | 3 |
| `dim_feedforward` | 512 |
| `dropout` | 0.1 |

---

## Ensemble Hyperparameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `alpha` | 1.0 | Ridge regularization strength |
| `fit_intercept` | True | Include bias term in Ridge |
| `use_scaler` | True | StandardScaler applied to meta-features |

---

## Evaluation Hyperparameters

| Parameter | Value |
|-----------|-------|
| Metrics | RMSE, MAE, R², SMAPE |
| `save_plots` | true |
| `compare_models` | true |

---

## Export Hyperparameters

| Parameter | Value |
|-----------|-------|
| Format | `torchscript` |
| Export dir | `models/exported` |

---

## Optimization Hyperparameters (Training Engine)

| Parameter | Value | Context |
|-----------|-------|---------|
| LR Scheduler | `ReduceLROnPlateau` | Reduces LR by factor 0.5 when val loss plateaus for 5 epochs |
| Early Stopping | `patience=10, min_delta=1e-6` | Stops training when val loss fails to improve |
| Weight initialization | Default PyTorch | No custom initialization |
| Gradient clipping | None | Not configured |

---

## Hyperparameter Summary Table

| Model | LR | Epochs | Hidden Dim | Layers | Dropout | Other |
|-------|----|--------|-----------|--------|---------|-------|
| Baseline | 0.001 | 50 | 64, 32 | 2 FC | 0.1 | seq_len=30 |
| LSTM | 0.001 | 100 | 128 | 2 | 0.2 | bidirectional=false |
| Transformer | 0.0005 | 100 | 128 | 3 enc | 0.1 | nhead=4, FF=512 |
| PatchTST | — | — | 128 | 3 enc | 0.1 | patch_len=8 |
| TimeMixer | — | — | 128 | 3 blocks | 0.1 | — |
| iTransformer | — | — | 128 | 3 enc | 0.1 | feature-transposed |
