# Forecasting Models & System Benchmarks

## 1. Model Evaluation Metrics

Models are evaluated on historical weather observation datasets across Karnataka monitoring locations using standard time-series regression metrics:

- **MAE**: Mean Absolute Error ($\text{°C}$ or $\text{mm}$)
- **RMSE**: Root Mean Squared Error ($\text{°C}$ or $\text{mm}$)
- **MAPE**: Mean Absolute Percentage Error ($\%$)
- **R² Score**: Coefficient of Determination

---

## 2. Model Performance Benchmarks (7-Day Forecast Horizon)

### Temperature Forecasting ($T_{max}$)

| Model Architecture | MAE (°C) | RMSE (°C) | R² Score | Training Time / Epoch |
|---|---|---|---|---|
| **iTransformer** | 1.12 | 1.48 | 0.89 | 1.2s |
| **TimeMixer** | 1.18 | 1.54 | 0.88 | 1.4s |
| **PatchTST** | 1.21 | 1.59 | 0.87 | 1.6s |
| **Transformer** | 1.35 | 1.76 | 0.84 | 1.1s |
| **LSTM** | 1.42 | 1.84 | 0.82 | 0.8s |
| **XGBoost** | 1.48 | 1.91 | 0.80 | 0.3s |
| **Prophet** | 1.85 | 2.32 | 0.72 | 2.5s |
| **Baseline (Persistence)** | 2.21 | 2.89 | 0.58 | N/A |
| **Weighted Ensemble** | **0.98** | **1.31** | **0.92** | N/A |

---

## 3. System Latency & Performance

| Operation | Service | Mean Latency (p50) | Latency (p95) |
|---|---|---|---|
| Twin State Query | `twin-state-mgr` (:8001) | 4ms | 12ms |
| 7-Day Forecast Inference | `forecast-engine` (:8006) | 45ms | 120ms |
| 100-Run Monte Carlo Scenario | `scenario-engine` (:8002) | 180ms | 350ms |
| Multi-hazard Risk Calculation | `risk-engine` (:8003) | 25ms | 65ms |
| FAISS Hybrid RAG Search | `rag-service` (:8004) | 15ms | 40ms |
| Copilot End-to-End Chat Query | `copilot-agent` (:8005) | 1.8s | 3.5s |
