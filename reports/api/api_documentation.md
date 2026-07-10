# API Documentation — Climate Digital Twin

## Overview

The system exposes 7 REST API services over HTTP, all behind a central API Gateway.

| Service | Base URL | Port | API Version |
|---|---|---|---|
| API Gateway | `http://localhost:8000` | 8000 | 1.0.0 |
| Twin State Manager | `http://localhost:8001` | 8001 | 1.0.0 |
| Scenario Engine | `http://localhost:8002` | 8002 | 1.0.0 |
| Risk Engine | `http://localhost:8003` | 8003 | 1.0.0 |
| RAG Service | `http://localhost:8004` | 8004 | 1.0.0 |
| Copilot Agent | `http://localhost:8005` | 8005 | 1.0.0 |
| Forecast Engine | `http://localhost:8006` | 8006 | 1.0.0 |

---

## 1. API Gateway (`backend/api/main.py`)

Central routing layer. Currently routes `/` to itself (no path-based routing implemented — services are accessed by port).

### Endpoints

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Health check | — | `{"status":"healthy","service":"fastapi-gateway","version":"1.0.0"}` |

### Error Codes

| Code | Description |
|---|---|
| 200 | Success |

---

## 2. Twin State Manager (`simulator/api/main.py`)

Digital Twin engine — entity model, state manager, versioning, event system, parquet repository. 7 endpoints.

### Endpoints

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Health check | — | `{"status":"healthy","service":"twin-state-mgr","version":"1.0.0"}` |
| GET | `/state/current` | Get current state for a location | `location_id: str` (query param) | `StateResponse` |
| GET | `/state/history` | Get historical states for a location | `location_id: str`, `time_range: str?` (query params) | `list[StateResponse]` |
| GET | `/state/version-history` | Get version history | `location_id: str` (query param) | `list[VersionHistoryItem]` |
| POST | `/state/sync` | Ingest a new observation | `SyncRequest` body | `SyncResponse` (201) |
| GET | `/forecast/state` | Get forecast state for a location | `location_id: str`, `horizon: str?` (query params) | `StateResponse` |
| POST | `/scenarios/simulate` | Apply a what-if scenario | `ScenarioRequest` body | `SyncResponse` (201) |
| POST | `/rollback` | Rollback twin to a version | `RollbackRequest` body | `RollbackResponse` |

### Request Schemas

**`StateRequest`**
```json
{"location_id": "string"}
```

**`SyncRequest`**
```json
{
  "location_id": "string",
  "latitude": 12.97,
  "longitude": 77.59,
  "district": "Bengaluru Urban",
  "timestamp": "2026-06-29T00:00:00",
  "rainfall": 0.0,
  "max_temp": 25.0,
  "min_temp": 18.0,
  "risk_score": 0.0,
  "prediction_confidence": 0.0,
  "data_source": "IMD"
}
```

**`ScenarioRequest`**
```json
{
  "location_id": "string",
  "scenario_id": "temp_increase_2",
  "rainfall_delta": 0.0,
  "max_temp_delta": 2.0,
  "min_temp_delta": 0.0
}
```

**`RollbackRequest`**
```json
{
  "location_id": "string",
  "version_id": 42
}
```

### Response Schemas

**`StateResponse`**
```json
{
  "location_id": "string",
  "timestamp": "string",
  "rainfall": 0.0,
  "max_temp": 0.0,
  "min_temp": 0.0,
  "risk_score": 0.0,
  "prediction_confidence": 0.0,
  "scenario_id": "string",
  "data_source": "string",
  "state_type": "string"
}
```

**`SyncResponse`** / **`RollbackResponse`**
```json
{
  "version_id": 1,
  "location_id": "string"
}
```

**`VersionHistoryItem`**
```json
{
  "version_id": 1,
  "timestamp": "string",
  "state_type": "string"
}
```

### Error Codes

| Code | Description |
|---|---|
| 200 | Success |
| 201 | Resource created |
| 404 | Location not found |
| 422 | Validation error (invalid coordinates, bounds, etc.) |

---

## 3. Scenario Engine (`simulator/scenarios/api.py`)

What-if simulation — temperature, rainfall, monsoon, extreme event scenarios. 6 endpoints.

### Endpoints

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Health check | — | `{"status":"healthy","service":"scenario-engine","version":"1.0.0"}` |
| POST | `/scenarios/create` | Create a scenario definition | `CreateScenarioRequest` body | `ScenarioDefinition` dict |
| POST | `/scenarios/simulate` | Run a scenario simulation | `SimulateRequest` body | `ScenarioRunResponse` |
| GET | `/scenarios` | List all scenarios | — | `list[ScenarioDefinition]` |
| GET | `/scenarios/{scenario_id}/compare` | Compare run with baseline | path param: `scenario_id` | `list[dict]` (deltas) |
| POST | `/scenarios/validate` | Validate scenario parameters | `ValidateRequest` body | `{"valid": bool, "errors": [str]}` |
| DELETE | `/scenarios/{scenario_id}` | Delete a custom scenario | path param: `scenario_id` | `{"deleted": true, "scenario_id": "str"}` |

### Request Schemas

**`CreateScenarioRequest`**
```json
{
  "scenario_id": "my_scenario",
  "name": "+2C Temperature",
  "description": "Increase temperature by 2 degrees",
  "scenario_type": "temperature",
  "parameters": {"delta": 2.0}
}
```
`scenario_type` must be one of: `temperature`, `rainfall`, `monsoon`, `extreme_event`, `combined`.

**`SimulateRequest`**
```json
{
  "scenario_id": "temp_increase_2",
  "location_ids": ["KA-BLR-001"]
}
```

**`ValidateRequest`**
```json
{
  "scenario_type": "temperature",
  "parameters": {"delta": 3.0}
}
```

### Response Schemas

**`ScenarioRunResponse`**
```json
{
  "run_id": "run_20260629_abc123",
  "scenario": {"id": "temp_increase_2", ...},
  "results": [{"location_id": "KA-BLR-001", "deltas": {...}}],
  "started_at": "2026-06-29T00:00:00",
  "completed_at": "2026-06-29T00:00:03",
  "total_duration_ms": 1234.5,
  "location_count": 1,
  "status": "completed"
}
```

### Error Codes

| Code | Description |
|---|---|
| 200 | Success |
| 201 | Scenario created |
| 404 | Scenario not found |

---

## 4. Risk Engine (`risk/api/main.py`)

Climate risk assessment — heat, flood, drought, composite scoring with SHAP explainability. 7 endpoints.

### Endpoints

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Health check | — | `{"status":"healthy","service":"risk-engine","version":"1.0.0"}` |
| POST | `/risk/assess` | Assess all risk types | `RiskAssessRequest` body | Full risk report dict |
| POST | `/risk/heat` | Assess heat risk only | `RiskAssessRequest` body | `HeatRiskScore` dict |
| POST | `/risk/flood` | Assess flood risk only | `RiskAssessRequest` body | `FloodRiskScore` dict |
| POST | `/risk/drought` | Assess drought risk only | `RiskAssessRequest` body | `DroughtRiskScore` dict |
| POST | `/risk/composite` | Assess composite risk only | `SimpleRiskRequest` body | `CompositeRiskScore` dict |
| POST | `/risk/report` | Generate full risk report | `RiskReportRequest` body | Report + output files |

### Request Schemas

**`RiskAssessRequest`**
```json
{
  "location_id": "KA-BLR-001",
  "district": "Bengaluru Urban",
  "max_temp": 38.0,
  "min_temp": 22.0,
  "rainfall": 10.0,
  "historical_mean_rainfall": 100.0,
  "historical_mean_temp": 28.0,
  "consecutive_hot_days": 5,
  "dry_period_days": 20,
  "multi_day_accumulation": 15.0,
  "seasonal_anomaly": 2.0,
  "forecast_uncertainty": 0.3,
  "prediction_confidence": 0.85
}
```

**`SimpleRiskRequest`**
```json
{
  "score": 45.0,
  "heat_score": 60.0,
  "flood_score": 30.0,
  "drought_score": 50.0
}
```

### Error Codes

| Code | Description |
|---|---|
| 200 | Success |

### Internal API Contract (`risk/api/contract.py`)

The `RiskAPI` abstract class defines 7 required methods used by downstream consumers:
- `calculate_risk()` — full risk assessment
- `calculate_heat_risk()` — heat risk only
- `calculate_flood_risk()` — flood risk only
- `calculate_drought_risk()` — drought risk only
- `generate_explanation()` — SHAP explanations
- `generate_report()` — report files
- `export_results()` — serialized output

---

## 5. Forecast Engine (`backend/services/forecast/main.py`)

ML forecasting — MLP, LSTM, Transformer models for rainfall/temperature prediction. 4 endpoints.

### Endpoints

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Health check | — | `{"status":"healthy","service":"forecast-engine","version":"1.0.0"}` |
| POST | `/forecast/predict` | Run forecast prediction | `PredictRequest` body | `PredictResponse` |
| GET | `/forecast/models` | List available models | — | `{"models": ["transformer", "lstm", "baseline"]}` |
| GET | `/forecast/model-info` | Get model metadata | — | Model config + status |

### Request Schema

**`PredictRequest`**
```json
{
  "location_id": "Karnataka",
  "horizon": 3,
  "model": "transformer"
}
```
- `horizon`: prediction horizon in steps (default: 3)
- `model`: one of `transformer`, `lstm`, `baseline` (default: transformer)

### Response Schema

**`PredictResponse`**
```json
{
  "location_id": "Karnataka",
  "horizon": 3,
  "model": "transformer",
  "predictions": [[25.3, 32.1, 18.5], [26.0, 33.0, 19.0]],
  "confidence_intervals": {
    "lower": [[24.0, 31.0, 17.5], [24.5, 32.0, 18.0]],
    "upper": [[26.6, 33.2, 19.5], [27.5, 34.0, 20.0]]
  },
  "metadata": {
    "model_type": "TransformerModel",
    "n_predictions": 2,
    "n_variables": 3
  }
}
```
Predictions shape: `(horizon, 3)` where 3 = [Rainfall, MaxTemp, MinTemp].

### Error Codes

| Code | Description |
|---|---|
| 200 | Success |
| 500 | Prediction error (model not loaded) |

---

## 6. RAG Service (`knowledge/api/main.py`)

RAG knowledge base — FAISS vector store, semantic search, document indexing. 2 endpoints.

### Endpoints

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Health check | — | `{"status":"healthy","service":"rag-service","version":"1.0.0"}` |
| POST | `/search` | Semantic search | `SearchRequest` body | `SearchResponse` |

### Request Schema

**`SearchRequest`**
```json
{
  "query": "karnataka monsoon rainfall",
  "top_k": 3
}
```

### Response Schema

**`SearchResponse`**
```json
{
  "query": "karnataka monsoon rainfall",
  "total_results": 3,
  "results": [
    {
      "chunk_id": "abc123",
      "document_id": "govt_001",
      "title": "Karnataka Climate Profile",
      "source": "government",
      "category": "government",
      "content": "Karnataka receives ...",
      "score": 0.763,
      "chunk_number": 1,
      "page_number": 0,
      "date": "",
      "region": "Karnataka",
      "keywords": ["rainfall", "monsoon"]
    }
  ]
}
```

### Error Codes

| Code | Description |
|---|---|
| 200 | Success |
| 500 | Search error |

---

## 7. Copilot Agent (`copilot/api/main.py`)

Climate Copilot — multi-agent LLM orchestration with conversation memory. 5 endpoints.

### Endpoints

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Health check (includes Ollama & tool status) | — | `{"status":"healthy","service":"copilot-agent","version":"1.0.0","ollama":{...},"tools":{...}}` |
| POST | `/ask` | Ask the Copilot a question | `AskRequest` body | `AskResponse` |
| POST | `/conversation` | Create a new conversation | — | `{"conversation_id": "uuid"}` |
| GET | `/conversation/{conversation_id}/history` | Get conversation history | path param | Conversation turns |
| GET | `/conversations` | List all conversations | — | List of conversation metadata |

### Request Schema

**`AskRequest`**
```json
{
  "query": "What is the flood risk for Bengaluru?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Response Schema

**`AskResponse`**
```json
{
  "answer": "Based on current data, Bengaluru has a Moderate flood risk (score: 45/100)...",
  "citations": ["Karnataka Climate Profile"],
  "intermediate_steps": [{"tool": "risk_tool", "input": {...}, "output": {...}}],
  "latency_ms": 2340.5,
  "intent": "risk_assessment"
}
```

### Copilot Intents

The system classifies queries into 8 intent types:

| Intent | Example Query | Tools Used |
|---|---|---|
| `forecast` | "What will the weather be like next week?" | forecast_tool |
| `twin_state` | "What is the current state of Bengaluru?" | twin_tool |
| `scenario` | "What if temperature increases by 2 degrees?" | scenario_tool |
| `risk_assessment` | "What is the drought risk?" | risk_tool |
| `rag_query` | "Tell me about IMD weather data" | rag_tool |
| `report` | "Generate a summary report for Karnataka" | report_tool (3 steps) |
| `greeting` | "Hello" | — (0 steps) |
| `unknown` | "What's the meaning of life?" | — (0 steps) |

### Error Codes

| Code | Description |
|---|---|
| 200 | Success |
| 400 | Bad request (empty query, LLM error) |
| 404 | Conversation not found |

---

## 8. Twin API Contract (`simulator/api/contract.py`)

The `TwinAPI` abstract class defines 6 methods used by all downstream modules:

| Method | Signature | Description |
|---|---|---|
| `get_current_state()` | `(location_id: str) -> dict \| None` | Latest observed state |
| `get_historical_state()` | `(location_id: str, time_range: str?) -> list[dict]` | Historical states |
| `get_forecast_state()` | `(location_id: str, horizon: str?) -> dict \| None` | Forecast state |
| `apply_scenario()` | `(scenario_parameters: dict) -> dict` | Apply scenario simulation |
| `rollback()` | `(version_id: int) -> dict` | Rollback to version |
| `get_state_history()` | `(location_id: str) -> list[dict]` | Version history |

The `TwinEngineAdapter` implements this contract wrapping `DigitalTwinEngine`.

---

## 9. Summary

| Service | Endpoints | Port | API Doc |
|---|---|---|---|
| API Gateway | 1 | 8000 | `GET /health` |
| Twin State Manager | 7 | 8001 | `GET /health` + OpenAPI at `/docs` |
| Scenario Engine | 6 | 8002 | `GET /health` + OpenAPI at `/docs` |
| Risk Engine | 7 | 8003 | `GET /health` + OpenAPI at `/docs` |
| RAG Service | 2 | 8004 | `GET /health` + OpenAPI at `/docs` |
| Copilot Agent | 5 | 8005 | `GET /health` + OpenAPI at `/docs` |
| Forecast Engine | 4 | 8006 | `GET /health` + OpenAPI at `/docs` |
| **Total** | **32** | — | — |

All FastAPI services expose automatic OpenAPI documentation at `/docs` (Swagger UI) and `/redoc` (ReDoc).
