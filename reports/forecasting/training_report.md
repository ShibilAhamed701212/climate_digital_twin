# Training Report — Climate Digital Twin

## Overview

The training pipeline is orchestrated by `models/run_forecast.py` and executed across three trained models (baseline, LSTM, transformer). It handles data loading, model creation, training with early stopping, evaluation, and export.

---

## Training Pipeline (`models/run_forecast.py`)

```
Step 1: Data Loading   → load_data() from data_loader.py
Step 2: Training        → train_model() from trainer.py (for each model)
Step 3: Evaluation      → evaluate_model() from evaluator.py (for each model)
Step 4: Export          → export_model() from predictor.py (best model only)
```

### Orchestration

1. Loads config from `models/configs/model_config.yaml`
2. Iterates over model names: `["baseline", "lstm", "transformer"]`
3. For each model:
   - Creates model via `predictor.create_model()`
   - Trains via `trainer.train_model()`
   - Saves training history as JSON
4. Evaluates all models on test set
5. Exports best model (lowest RMSE) to TorchScript format

---

## Data Loading (`models/data_loader.py`)

### `ClimateDataset` (PyTorch `Dataset`)

Creates sliding windows of length `sequence_length` (30) from the input data.

```
Dataset length = len(data) - sequence_length
__getitem__(idx) → (features[idx:idx+30], targets[idx+30])
```

- **Features tensor:** shape `(num_samples, 30, 11)` — float32
- **Targets tensor:** shape `(num_samples, 3)` — float32

### Data Sources

1. **Processed CSVs** (preferred):
   - `data/processed/training.csv` (439,740 rows)
   - `data/processed/validation.csv` (94,230 rows)
   - `data/processed/testing.csv` (94,230 rows)
   - Categorical columns (Season) encoded via `pd.Categorical.codes`

2. **Synthetic fallback** (when CSVs not found):
   - Generated via `_generate_synthetic_training_data(5000, 30)`
   - Train/val/test split: 3500 / 750 / 750 samples

### `Scaler` (Min-Max Normalization)

A custom min-max scaler class:

- `fit(data)`: computes per-column min/max from training data
- `transform(data)`: normalizes to [0, 1] range: `(data - min) / (max - min)`
- `inverse_transform(data)`: restores original scale: `data * (max - min) + min`
- Handles zero-range columns by setting `max = min + 1`

Two scalers are fitted:
- `feat_scaler` — normalizes feature columns
- `tgt_scaler` — normalizes target columns

### DataLoaders

| Split | Batch Size | Shuffle | Samples |
|-------|-----------|---------|---------|
| Training | 64 | Yes | 439,740 |
| Validation | 64 | No | 94,230 |
| Testing | 64 | No | 94,230 |

---

## Training Engine (`models/trainer.py`)

### Device Selection

```python
def get_device(device_pref="auto"):
    # Returns cuda if available, else cpu
```

### Reproducibility

```python
set_random_seed(seed=42)  # Sets Python, NumPy, and PyTorch seeds
```

### Loss Functions

| Name | Function |
|------|----------|
| `mse` | `nn.MSELoss()` — Mean Squared Error |
| `mae` | `nn.L1Loss()` — Mean Absolute Error |

**Default:** MSE

### Optimizers

| Name | Function |
|------|----------|
| `adam` | `torch.optim.Adam` |
| `sgd` | `torch.optim.SGD` |

**Default:** Adam

### Learning Rate Scheduler

`ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)`

Reduces LR by half when validation loss plateaus for 5 epochs.

### Training Loop (`train_model()`)

```
For each epoch (1 to max_epochs):
    train_loss = train_one_epoch(model, train_loader, loss_fn, optimizer, device)
    val_loss   = validate_one_epoch(model, val_loader, loss_fn, device)
    scheduler.step(val_loss)
    
    If val_loss < best_val_loss:
        Save checkpoint: models/checkpoints/{model_name}_best.pt
        Update best_val_loss and best_epoch
    
    early_stopping(val_loss)
    If early_stop triggered: break
```

### `EarlyStopping`

| Parameter | Value |
|-----------|-------|
| `patience` | 10 epochs |
| `min_delta` | 1e-6 |
| Trigger condition | Validation loss does not improve by min_delta for patience epochs |

### `train_one_epoch()`

1. Sets model to train mode
2. Iterates over batches: `(x, y)`
3. Forward pass → loss → backward → optimizer step
4. Returns average loss over all batches

### `validate_one_epoch()`

1. Sets model to eval mode
2. Iterates over batches with `torch.no_grad()`
3. Returns average validation loss

### Return Value

```python
history = {
    "train_loss": [...],      # list of per-epoch training losses
    "val_loss": [...],        # list of per-epoch validation losses
    "best_epoch": int,        # epoch with lowest val_loss
    "best_val_loss": float,   # minimum validation loss achieved
    "epochs_trained": int,    # actual epochs run (may be < max due to early stopping)
    "model_name": str,        # model identifier
    "elapsed_seconds": float, # total training time
}
```

History is saved as JSON to `models/evaluation/{model_name}_history.json`.

---

## Physics Validation (`models/physics.py`)

**Class:** `PhysicsValidator`

A deterministic, stateless, model-agnostic safety layer applied to all predictions.

### Constraints

| Variable | Constraint | Default |
|----------|-----------|---------|
| Rainfall | Clamp to [0, rainfall_upper] | 500 mm/day |
| MaxTemp | Clamp to [temp_lower, temp_upper] | [-10, 55] °C |
| MinTemp | Clamp to [temp_lower, temp_upper] | [-10, 55] °C |
| Tmin vs Tmax | Swap if Tmin > Tmax | — |

### Properties

- **Deterministic:** Same input → same output
- **Idempotent:** Double application yields same result
- **Thread-safe:** Pure tensor operations only
- **Model-agnostic:** Works with any model output

**Note:** This is a safety layer, not a simulation. It only prevents physically impossible values.

---

## Prediction (`models/predictor.py`)

### `create_model(model_name, n_features, n_targets, config)`

Model registry dict:

| Name | Class |
|------|-------|
| `baseline` | `BaselineModel` |
| `lstm` | `LSTMModel` |
| `transformer` | `TransformerModel` |

### `load_model(model_name, checkpoint_path, n_features, n_targets, config)`

1. Creates model instance
2. Loads state dict from checkpoint with `weights_only=True`
3. Sets model to eval mode

### `predict(model, input_data, target_scaler=None)`

1. Runs inference with `torch.no_grad()`
2. Inverse-transforms predictions if scaler provided
3. Applies physics validation
4. Computes 95% confidence intervals: `pred ± 1.96 * std`
5. Returns dict with `predictions`, `confidence_intervals`, `metadata`

### `export_model(model, path)`

Exports model to TorchScript format using `torch.jit.script()`.

---

## Evaluation Metrics (`models/evaluator.py`)

### Metrics Computed

| Metric | Formula | Range | Notes |
|--------|---------|-------|-------|
| **RMSE** | `sqrt(mean((y_true - y_pred)²))` | [0, ∞) | Lower is better |
| **MAE** | `mean(|y_true - y_pred|)` | [0, ∞) | Lower is better |
| **R²** | `1 - SS_res / SS_tot` | [0, 1] | Higher is better |
| **SMAPE** | `100 × mean(2|y-p| / (|y|+|p|+ε))` | [0, 200]% | Lower is better; handles zero rainfall |

### Evaluation Outputs

1. **Metrics JSON:** `models/evaluation/model_comparison.json` — per-model metrics
2. **Plots** (per model per target):
   - Predictions vs Actuals scatter plot
   - Error distribution histogram
   - Residuals vs Predicted scatter plot
   - Saved to `models/evaluation/{model_name}_{target}_eval.png`
3. **Training history:** `models/evaluation/{model_name}_history.json`

### Plotting

- Uses `matplotlib` with `Agg` backend (non-interactive)
- Resolution: 100 dpi, figure size 15×4 inches (3 panel layout)

---

## Training Configuration Summary

| Parameter | Value |
|-----------|-------|
| Sequence length | 30 days |
| Batch size | 64 |
| Loss function | MSE |
| Optimizer | Adam |
| Early stopping patience | 10 |
| LR scheduler | ReduceLROnPlateau (factor=0.5, patience=5) |
| Random seed | 42 |
| Validation frequency | Every epoch |
| Device | Auto (CPU/GPU) |

### Per-Model Training Config

| Model | Learning Rate | Max Epochs | Additional |
|-------|--------------|------------|------------|
| Baseline | 0.001 | 50 | hidden_layers=[64,32] |
| LSTM | 0.001 | 100 | hidden_dim=128, num_layers=2, dropout=0.2 |
| Transformer | 0.0005 | 100 | d_model=128, nhead=4, num_layers=3 |
