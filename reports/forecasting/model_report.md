# Forecast Model Report — Climate Digital Twin

## Overview

Six model architectures are implemented across `models/`. Three are fully trained (baseline, LSTM, transformer); three are stubs (PatchTST, TimeMixer, iTransformer). An ensemble meta-learner combines base model predictions. Models are registered in `models/registry/metadata.json`.

---

## Model Inventory

| Model | Architecture Type | Trained | Checkpoint | Checkpoint Size | RMSE | R² |
|-------|-------------------|---------|------------|----------------|------|----|
| Baseline | Feed-Forward MLP | Yes | `models/checkpoints/baseline_best.pt` | 94.5 KB | 4.59 | 0.87 |
| LSTM | LSTM (2-layer) | Yes | `models/checkpoints/lstm_best.pt` | 802.3 KB | 4.53 | 0.87 |
| Transformer | Transformer Encoder | Yes | `models/checkpoints/transformer_best.pt` | 2,847.1 KB | 4.57 | 0.87 |
| PatchTST | Patch + Transformer | No (stub) | — | — | — | — |
| TimeMixer | MLP-mixer blocks | No (stub) | — | — | — | — |
| iTransformer | Feature-transposed Transformer | No (stub) | — | — | — | — |
| Ensemble | Ridge meta-learner | Fitted | — | — | — | — |

---

## Baseline (`models/baseline/model.py`)

**Class:** `BaselineModel(nn.Module)`

A simple multi-layer perceptron that flattens the sequence dimension and passes through configurable hidden layers.

### Architecture

| Layer | Description |
|-------|-------------|
| Input | Flatten: `(batch, 30, 11) → (batch, 330)` |
| Hidden 1 | `Linear(330, 64)` + ReLU + Dropout(0.1) |
| Hidden 2 | `Linear(64, 32)` + ReLU + Dropout(0.1) |
| Output | `Linear(32, 3)` → `(batch, 3)` |

**Parameters:** ~21,000 (input 330 → 64 → 32 → 3)
**Config:** `hidden_layers=[64, 32]`, `dropout=0.1`, `learning_rate=0.001`, `epochs=50`

### Training

- Optimizer: Adam (lr=0.001)
- Best checkpoint saved by validation loss
- Patience-based early stopping (patience=10)

### Performance (from metadata.json)

- RMSE: **4.59** (highest — worst performing)
- R²: **0.87**

---

## LSTM (`models/lstm/model.py`)

**Class:** `LSTMModel(nn.Module)`

A stacked LSTM that processes the full sequence and uses the final hidden state for prediction.

### Architecture

| Layer | Description |
|-------|-------------|
| Input | `(batch, 30, 11)` |
| LSTM | 2 layers, hidden_dim=128, dropout=0.2, batch_first=True |
| Output | `Linear(128, 3)` on last timestep `(batch, 3)` |

**Parameters:** ~145,000 (LSTM: 4 layers of gates × 128² + 11→128; FC: 128×3)
- LSTM params per layer: `4 * (hidden_size * (input_size + hidden_size) + hidden_size)`
  - Layer 1: `4 * (128 * (11 + 128) + 128) = 71,680`
  - Layer 2: `4 * (128 * (128 + 128) + 128) = 131,584`
- FC: `128 * 3 + 3 = 387`
- Total: ~203,651

**Config:** `hidden_dim=128`, `num_layers=2`, `dropout=0.2`, `bidirectional=false`, `learning_rate=0.001`, `epochs=100`

### Checkpoint

- **802.3 KB** — `models/checkpoints/lstm_best.pt`

### Performance

- RMSE: **4.53** (best among trained models)
- R²: **0.87**

---

## Transformer (`models/transformer/model.py`)

**Class:** `TransformerModel(nn.Module)`

A Transformer encoder with sinusoidal positional encoding for climate forecasting.

### Architecture

| Layer | Description |
|-------|-------------|
| Input Projection | `Linear(11, 128)` |
| Positional Encoding | Sinusoidal PE (max_len=1000) |
| Encoder | 3 layers, nhead=4, d_model=128, dim_feedforward=512, dropout=0.1 |
| Output | `Linear(128, 3)` on last timestep |

**Parameters:** ~1,350,000
- Input proj: `11*128 + 128 = 1,536`
- Each encoder layer (4-head self-attn + FFN):
  - Self-attn: `QKV = 3 * (128*128 + 128) = 49,536`, output: `128*128 + 128 = 16,512`
  - FFN: `128*512 + 512 + 512*128 + 128 = 131,584`
  - Layer norms: 2 × (128+128) = 512
  - Total per layer: ~198,144
- 3 layers: ~594,432
- Output FC: `128*3 + 3 = 387`
- Total: ~596,355

**Config:** `d_model=128`, `nhead=4`, `num_encoder_layers=3`, `dim_feedforward=512`, `dropout=0.1`, `learning_rate=0.0005`, `epochs=100`

### Checkpoint

- **2,847.1 KB** — `models/checkpoints/transformer_best.pt`
- **2,910.2 KB** (TorchScript export) — `models/exported/transformer_best.pt`

### Performance

- RMSE: **4.57**
- R²: **0.87**

---

## PatchTST (`models/patchtst/model.py`) — Stub

**Class:** `PatchTSTModel(nn.Module)`

A patch-based Transformer that divides the sequence into patches before encoding.

### Architecture

| Layer | Description |
|-------|-------------|
| Patch Embedding | Patches of length 8, `Linear(8*11, 128)` |
| Transformer Encoder | 3 layers, nhead=4, d_model=128, dim_feedforward=512 |
| Output | Mean pooling over patches → `Linear(128, 3)` |

**Status:** **Untrained stub.** Architecture is implemented but no checkpoint exists and the model is not trained in the pipeline (`run_forecast.py` only trains baseline, lstm, transformer).

---

## TimeMixer (`models/timemixer/model.py`) — Stub

**Class:** `TimeMixerModel(nn.Module)`

An MLP-mixer style architecture with residual blocks applied per timestep.

### Architecture

| Layer | Description |
|-------|-------------|
| Input Projection | `Linear(11, 128)` |
| Mixer Blocks | 3× `LayerNorm → MLP(128→512→128) + residual` |
| Output | `Linear(128, 3)` on last timestep |

**Status:** **Untrained stub.**

---

## iTransformer (`models/itransformer/model.py`) — Stub

**Class:** `ITransformerModel(nn.Module)`

A variant that transposes the input to treat features as the sequence dimension (time as channels).

### Architecture

| Layer | Description |
|-------|-------------|
| Transpose | `(batch, time, features) → (batch, features, time)` |
| Time Projection | `Linear(1, 128)` per time point |
| Mean pooling | Pool over features dimension |
| Transformer Encoder | 3 layers, nhead=4, d_model=128 |
| Output | Mean pooling over sequence → `Linear(128, 3)` |

**Status:** **Untrained stub.**

---

## Ensemble (`models/ensemble/meta_learner.py`)

**Class:** `EnsembleMetaLearner`

A stacking ensemble with a Ridge regression meta-learner.

### Architecture

- **Input:** Concatenated predictions from all base models
- **Scaler:** `StandardScaler` per target (optional)
- **Meta-learner:** `Ridge(alpha=1.0, fit_intercept=True)` — one per target variable
- **Output:** Weighted combination of base model predictions

### Key Features

- Fitted per-target (3 separate Ridge models for Rainfall, MaxTemp, MinTemp)
- Supports weight extraction via `get_weights()` which returns coefficient per base model per target
- Serialization via `joblib`
- Requires minimum 2 base models

**Status:** Fitted on stacking of baseline, LSTM, and transformer predictions (see `run_forecast.py`).

---

## Model Registry (`models/registry.py`)

**Class:** `ModelRegistry`

JSON-backed registry at `models/registry/metadata.json`.

### Registered Models (from metadata.json)

| Name | Architecture | Version | Registered | RMSE | R² |
|------|-------------|---------|------------|------|----|
| baseline | BaselineModel | 1.0.0 | 2026-06-29T01:06:26 | 4.59 | 0.87 |
| lstm | LSTMModel | 1.0.0 | 2026-06-29T01:06:26 | 4.53 | 0.87 |
| transformer | TransformerModel | 1.0.0 | 2026-06-29T01:06:26 | 4.57 | 0.87 |

### Registry Features

- Register, get, list, update metrics, delete models
- `get_best(metric="rmse")` returns model with lowest RMSE
- `get_available_architectures()` returns unique architecture types

---

## Model Config (`models/configs/model_config.yaml`)

Common configuration:

| Parameter | Value |
|-----------|-------|
| `sequence_length` | 30 days |
| `batch_size` | 64 |
| `feature_columns` | 11 (Rainfall, MaxTemp, MinTemp, Month, Week, Season, Monsoon, RollingRain7, RollingRain30, RollingTemp7, RollingTemp30) |
| `target_columns` | 3 (Rainfall, MaxTemp, MinTemp) |
| `training.loss` | MSE |
| `training.optimizer` | Adam |
| `training.early_stopping_patience` | 10 |
| `training.random_seed` | 42 |
| `evaluation.metrics` | RMSE, MAE, R², SMAPE |
| `export.format` | TorchScript |

Per-model hyperparameters are documented in the Hyperparameter Report.
