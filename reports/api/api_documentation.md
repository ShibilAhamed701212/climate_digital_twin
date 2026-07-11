# API Documentation

> **⚠️ All endpoints return synthetic data. No real API integration tested.**

---

## Forecasting API (Port 8005)

### `GET /health`
**Response:** `{"status": "healthy", "service": "forecasting"}`

### `POST /predict`
Generate forecast for a location.

**Request:**
```json
{
  "location": "kalaburagi",
  "days": 7,
  "model": "lstm"
}
```

**Response:**
```json
{
  "predictions": [
    {"date": "2024-01-01", "precipitation": 12.3, "t2m_max": 32.1, "t2m_min": 21.5}
  ],
  "model": "lstm",
  "location": "kalaburagi",
  "metrics": {"rmse": 4.53, "r2": 0.87}
}
```

**Notes:**
- `model` can be: `mlp`, `lstm`, `transformer`, `ensemble` (mock)
- Stub models (patchtst, timemixer, itransformer) return 400
- All predictions based on synthetic data

### `GET /models`
List available models.

**Response:**
```json
{
  "models": [
    {"name": "mlp", "status": "trained", "rmse": 4.59},
    {"name": "lstm", "status": "trained", "rmse": 4.53},
    {"name": "transformer", "status": "trained", "rmse": 4.57},
    {"name": "patchtst", "status": "stub"},
    {"name": "timemixer", "status": "stub"},
    {"name": "itransformer", "status": "stub"},
    {"name": "ensemble", "status": "mock"}
  ]
}
```

---

## Digital Twin API (Port 8002)

### `GET /health`
**Response:** `{"status": "healthy", "service": "twin"}`

### `GET /state/{location}`
Get current twin state.

**Response:**
```json
{
  "location": "kalaburagi",
  "version_id": 42,
  "state_type": "CURRENT",
  "timestamp": "2024-01-01T00:00:00",
  "data": {"temperature": 28.5, "precipitation": 12.3, ...}
}
```

### `GET /state/{location}/history`
Get state history.

### `POST /state/{location}`
Update state (creates new version).

---

## Scenario Engine (Port 8003)

### `GET /health`

### `POST /scenario/run`
Run a scenario simulation.

**Request:**
```json
{
  "scenario_id": "T2",
  "locations": ["kalaburagi", "mysuru"]
}
```

**Response:**
```json
{
  "scenario": "T2 (+2°C Warming)",
  "results": {
    "kalaburagi": {"delta_temperature": 2.0, "baseline": {...}, "scenario": {...}},
    "mysuru": {"delta_temperature": 2.0, "baseline": {...}, "scenario": {...}}
  },
  "execution_time_ms": 45
}
```

### `GET /scenarios`
List available scenarios.

---

## Risk API (Port 8004)

### `GET /health`

### `POST /risk/heat`
Compute heat risk.

**Request:**
```json
{
  "location": "kalaburagi",
  "features": {"t2m_max": 38.0, "hot_days": 5, "anomaly": 2.1}
}
```

**Response:**
```json
{
  "location": "kalaburagi",
  "risk_type": "heat",
  "score": 72.5,
  "category": "High",
  "components": {"max_temp": 30.0, "hot_days": 25.0, "anomaly": 17.5}
}
```

### `POST /risk/flood`
### `POST /risk/drought`
### `POST /risk/composite`

---

## RAG API (Port 8006)

### `GET /health`

### `POST /query`
Retrieve relevant chunks.

**Request:**
```json
{
  "query": "What climate risks affect Karnataka?"
}
```

**Response:**
```json
{
  "results": [
    {"text": "...", "score": 0.712, "metadata": {"category": "risk", "source": "..."}}
  ],
  "total_chunks": 5
}
```

### `POST /index`
Index documents from data directory.

---

## Copilot API (Port 8007)

### `GET /health`

### `POST /ask`
Ask a question (mock response).

**Request:**
```json
{
  "query": "What's the flood risk in Kalaburagi?",
  "conversation_id": "abc-123"
}
```

**Response:**
```json
{
  "response": "The flood risk level for Kalaburagi is moderate.",
  "intent": "RISK",
  "conversation_id": "abc-123",
  "execution_time_ms": 45
}
```

### `GET /conversation/{id}`
Get conversation history.
