# System Architecture & Technical Specifications

## 1. System Design Goals

- **Modular Microservices**: Decoupled domain services allowing independent scaling and maintenance.
- **Physics-Informed Data Integrity**: Hard physical bounds enforced on all predictions and state transitions.
- **High Observability**: Built-in health endpoints, structured JSON logging, and optional Prometheus/Grafana metrics.
- **Hybrid Data Processing**: Real-time Open-Meteo & NASA POWER data integration combined with historical ERA5 reanalysis.

---

## 2. Component Specifications

### 2.1 API Gateway Layer (`backend/api/`)
- Built on **FastAPI** 0.109+ and **Uvicorn** ASGI server.
- Provides standard REST endpoints with Pydantic v2 data validation schemas.
- Handles centralized CORS policy, rate limiting, and exception handling.

### 2.2 Domain Simulation Layer (`climatedt/` & `simulator/`)
- **Penman-Monteith ET0**: $ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$
- **SCS Curve Number Runoff**: $Q = \frac{(P - I_a)^2}{(P - I_a) + S}$
- **SPEI Drought Index**: Log-logistic distribution fitting over climate water balance $(P - ET_0)$.

### 2.3 Machine Learning Subsystem (`models/`)
- **PyTorch** deep learning pipeline supporting sequence-to-sequence forecasting.
- Automated feature scaling via `StandardScaler` / `MinMaxScaler`.
- Weighted model ensemble:
  $$\hat{y} = \sum_{m=1}^{M} w_m f_m(x)$$
  where weights $w_m$ are dynamically inverse-proportional to validation MAE.

### 2.4 Knowledge Retrieval & RAG (`knowledge/`)
- Dense embeddings generated via `sentence-transformers/all-MiniLM-L6-v2`.
- Indexing powered by `faiss-cpu` (FlatIP / HNSW).
- Hybrid search fusion score:
  $$Score_{hybrid} = \alpha \cdot Score_{semantic} + (1 - \alpha) \cdot Score_{BM25}$$

---

## 3. Storage Layer Architecture

| Store Name | Storage Engine | Location / Directory | Primary Purpose |
|---|---|---|---|
| Twin Store | Apache Parquet | `data/twin_store/` | Versioned climate entity historical states |
| Forecast Store | Parquet / JSON | `data/forecasts/` | Generated model predictions and metadata |
| Scenario Store | Parquet | `data/scenarios/` | Monte Carlo simulation trajectory outputs |
| Vector Store | FAISS Binary Index | `knowledge/vector_store/` | Semantic document embeddings |
| Model Registry | JSON / PyTorch `.pt` | `models/checkpoints/` | Trained model weights and hyperparams |
