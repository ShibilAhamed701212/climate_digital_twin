# Forecast Inference Report — Climate Digital Twin

## Overview

The inference service is implemented as a **FastAPI** application that loads a trained model and serves predictions via REST API. The service is located in `backend/services/forecast/`.

---

## Architecture

```
Client Request → FastAPI (main.py) → ForecastInference (inference.py) → Data Loader → Model → Physics Validator → Response
```

### Components

- **`backend/services/forecast/main.py`** — FastAPI application entry point
- **`backend/services/forecast/inference.py`** — `ForecastInference` class handling model loading, data retrieval, and prediction orchestration
- **`models/predictor.py`** — Core `predict()` function with physics validation
- **`models/physics.py`** — Physics safety layer

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/forecast/predict` | Run forecast prediction |
| `GET` | `/forecast/models` | List available models |
| `GET` | `/forecast/model-info` | Get current model metadata |

### POST `/forecast/predict`

**Request:**
```json
{
  "location_id": "Karnataka",
  "horizon": 3,
  "model": "transformer"
}
```

**Response:**
```json
{
  "location_id": "Karnataka",
  "horizon": 3,
  "model": "transformer",
  "predictions": [[rain, maxtemp, mintemp], ...],
  "confidence_intervals": {
    "lower": [[...], ...],
    "upper": [[...], ...]
  },
  "metadata": {
    "model_type": "TransformerModel",
    "n_predictions": 1,
    "n_variables": 3
  }
}
```

**Default model:** `transformer` (the best-performing architecture)

---

## `ForecastInference` Class (`inference.py`)

### Initialization

```python
class ForecastInference:
    def __init__(self, model_name="transformer"):
        # Load config from models/configs/model_config.yaml
        # Set device (auto: CUDA or CPU)
        # Determine n_features (11) and n_targets (3)
        # Load model from checkpoint or TorchScript export
        # Load target scaler from pickle
        # Initialize PhysicsValidator
        # Check model registry
```

### Model Loading (`_load_best_model()`)

1. **Priority 1:** TorchScript export at `models/exported/{model_name}_best.pt`
   - Loads via `torch.jit.load()`
2. **Priority 2:** State dict checkpoint at `models/checkpoints/{model_name}_best.pt`
   - Loads via `predictor.load_model()` which uses `torch.load(weights_only=True)`
3. **Fallback:** Raises `FileNotFoundError` if neither exists

### Scaler Loading (`_load_scaler()`)

- Loads target scaler from **pickle** file at `models/exported/target_scaler.pkl`
- Uses `pickle.load()` to deserialize the `Scaler` object
- If scaler is unavailable, continues with un-scaled predictions (warning logged)
- Error handling: catches `UnpicklingError`, `AttributeError`, `EOFError`

### Real Data Loading (`_load_latest_data()`)

1. Searches for processed CSV files in order:
   - `data/processed/testing.csv` (preferred)
   - `data/processed/validation.csv`
   - `data/processed/training.csv`
2. Takes the **last `sequence_length` (30) rows** for the selected feature columns
3. Converts to PyTorch tensor: shape `(1, 30, 11)`

**Fallback:** If no CSV files exist or none have enough rows:
- Generates synthetic data using `numpy.random.default_rng(42).uniform(0, 1, (30, 11))`
- A warning is logged: `"Fallback synthetic data used for input"`

### Prediction Pipeline (`predict()`)

```
1. Load latest data (or accept input_data parameter)
2. Run model inference: model(input_data)
3. Inverse-transform predictions via target_scaler (if available)
4. Apply physics validation (clamp rainfall, ensure Tmin ≤ Tmax, clamp temperatures)
5. Compute 95% confidence intervals: pred ± 1.96 * std
6. Return structured response with predictions, CIs, and metadata
```

---

## Data Flow Diagram

```
┌─────────────┐     ┌─────────────────────────────────────┐     ┌──────────────┐
│  API Client  │────▶│        ForecastInference            │────▶│   Response   │
└─────────────┘     │                                     │     └──────────────┘
                    │  ┌───────────┐   ┌────────────────┐  │
                    │  │ Model     │   │ Target Scaler  │  │
                    │  │ (transformer_best.pt) │   │ (target_scaler.pkl) │  │
                    │  └───────────┘   └────────────────┘  │
                    │         │                 │          │
                    │         ▼                 ▼          │
                    │  ┌─────────────────────────────┐     │
                    │  │     PhysicsValidator        │     │
                    │  │  - Clamp rainfall [0, 500]  │     │
                    │  │  - Swap Tmin/Tmax if needed │     │
                    │  │  - Clamp temp [-10, 55]     │     │
                    │  └─────────────────────────────┘     │
                    │                                     │
                    │  ┌─────────────────────────────┐     │
                    │  │  Data Loader                │     │
                    │  │  - testing.csv (preferred)  │     │
                    │  │  - validation.csv           │     │
                    │  │  - training.csv (fallback)  │     │
                    │  │  - Synthetic (last resort)  │     │
                    │  └─────────────────────────────┘     │
                    └─────────────────────────────────────┘
```

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| No checkpoint found | `FileNotFoundError` with checked paths |
| Scaler not found | Warning logged, un-scaled predictions used |
| Corrupted scaler pickle | `pickle.UnpicklingError` caught, un-scaled predictions used |
| CSV file not found | Falls through to next CSV source |
| CSV has insufficient rows (< 30) | Falls through to next CSV source |
| No data available at all | Synthetic data generated with seed 42 |
| Prediction failure | `PredictionError` raised with wrapped exception |
| Model not in registry | Warning logged, inference continues |

---

## Model Selection

The default model is `transformer`. Available models are discovered by scanning:

- `models/checkpoints/*_best.pt` — state dict checkpoints
- `models/exported/*_best.pt` — TorchScript exports

The inference API provides:
- `GET /forecast/models` — lists all available models
- `GET /forecast/model-info` — returns current model configuration details

---

## Service Configuration

| Parameter | Value |
|-----------|-------|
| API Framework | FastAPI |
| Service Title | "Forecast Engine" |
| Version | "1.0.0" |
| Default Model | transformer |
| Checkpoint Directory | `models/checkpoints/` |
| Export Directory | `models/exported/` |
| Scaler Path | `models/exported/target_scaler.pkl` |
| Config Path | `models/configs/model_config.yaml` |
| Sequence Length | 30 |
| Features | 11 |
| Targets | 3 |

---

## Running the Service

The service can be started via the FastAPI application:

```bash
uvicorn backend.services.forecast.main:app --reload
```

The `/health` endpoint returns:
```json
{"status": "healthy", "service": "forecast-engine", "version": "1.0.0"}
```
