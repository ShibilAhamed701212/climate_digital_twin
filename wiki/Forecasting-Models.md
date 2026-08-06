# Forecasting Models

## Overview

The Climate Digital Twin includes an extensive ML forecasting suite (`models/`) capable of predicting climate variables across multiple time horizons (1-day, 3-day, and 7-day). The platform features 8 model architectures, automated model training and validation, hyperparameter tuning, model versioning/registration, and ensemble prediction with physical constraint validation.

---

## Supported Architectures

| Architecture | Directory | Category | Strengths |
|---|---|---|---|
| **LSTM** | `models/lstm/` | Deep Learning | Sequential memory, seasonal pattern learning |
| **Transformer** | `models/transformer/` | Deep Learning | Multi-head attention over historical time series |
| **iTransformer** | `models/itransformer/` | Deep Learning | Inverted Transformer treating variables as tokens for cross-variate dependence |
| **PatchTST** | `models/patchtst/` | Deep Learning | Patching time series for long-horizon spatial-temporal accuracy |
| **TimeMixer** | `models/timemixer/` | Deep Learning | Multi-scale temporal mixing for complex weather patterns |
| **XGBoost** | `models/xgboost/` | Gradient Boosting | Fast tabular prediction with engineered lag features |
| **Prophet** | `models/prophet/` | Statistical | Robust trend + additive seasonality modeling |
| **Baseline** | `models/baseline/` | Statistical | Persistence and historical climatology baseline |

---

## Model Pipeline & Workflow

```
Raw Climate Data ──► Feature Engineering ──► Dataset Builder ──► Model Trainer ──► Registry
                          (Lags, Rolling)     (Sequence Windows)   (PyTorch/XGBoost)   (Checkpoints)
                                                                                            │
                                                                                            ▼
                                                                                   Ensemble Predictor
                                                                                            │
                                                                                            ▼
                                                                                  Physics Validation
                                                                                            │
                                                                                            ▼
                                                                                  Inference API (:8006)
```

---

## Model Registry & Versioning (`ModelRegistry`)

The `ModelRegistry` handles lifecycle management for trained model artifacts:
- Registers model metadata, metrics (RMSE, MAE, $R^2$), hyperparameters, and weights.
- Manages active, candidate, and archived model versions.
- Loads optimal checkpoints automatically during inference requests.

```python
from models.registry import ModelRegistry

registry = ModelRegistry()

# List registered models
active_models = registry.list_models(status="ACTIVE")

# Get best model for temperature forecasting
best_model = registry.get_best_model(target="max_temp", metric="rmse")
```

---

## Physics-Informed Post-Processing (`physics.py`)

All model predictions undergo physical constraint validation to prevent physically impossible forecasts:
- **Temperature Constraints**: $T_{min} \le T_{max}$, physical range bounds (e.g., $-10^\circ C \le T \le 55^\circ C$).
- **Rainfall Constraints**: Non-negativity ($Rainfall \ge 0$).
- **Humidity Bounds**: $0\% \le Relative Humidity \le 100\%$.

---

## Training & CLI Commands

```bash
# Run training for default ensemble models
python models/run_forecast.py

# Command-line interface for specific models
python models/forecast_cli.py --model transformer --epochs 50 --lr 0.001 --horizon 7

# Register trained checkpoints
python scripts/register_models.py
```
