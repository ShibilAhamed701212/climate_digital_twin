# API Reference

## Base URL

```
http://localhost:8000
```

All endpoints are served through the FastAPI gateway. Interactive API documentation (Swagger UI) is available at `/docs`.

---

## Health Endpoints

### `GET /health`
Returns overall service health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-08-07T00:00:00Z",
  "version": "0.1.0"
}
```

### `GET /health/ready`
Returns readiness status for all downstream services.

---

## Twin State Endpoints

### `GET /twin/state`
Retrieve the current digital twin state for a location.

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `location_id` | string | Location identifier (e.g., `KA-BLR-001`) |

**Response:**
```json
{
  "location_id": "KA-BLR-001",
  "timestamp": "2026-08-07T00:00:00Z",
  "max_temp": 32.5,
  "min_temp": 22.1,
  "rainfall": 12.3,
  "humidity": 68.0,
  "version": 42
}
```

### `GET /twin/state/history`
Retrieve historical twin state versions.

### `POST /twin/state`
Update the twin state with a new observation.

---

## Forecast Endpoints

### `GET /forecast/predict`
Generate climate forecasts for a location.

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `location_id` | string | Location identifier |
| `horizon` | integer | Forecast horizon in days (1, 3, or 7) |
| `model` | string | Model name (optional; defaults to ensemble) |

**Response:**
```json
{
  "location_id": "KA-BLR-001",
  "horizon_days": 7,
  "model": "ensemble",
  "predictions": [
    {
      "date": "2026-08-08",
      "max_temp": 31.2,
      "min_temp": 21.8,
      "rainfall": 15.4
    }
  ]
}
```

---

## Scenario Endpoints

### `POST /scenario/simulate`
Run a what-if climate scenario simulation.

**Request Body:**
```json
{
  "location_id": "KA-BLR-001",
  "scenario_type": "temperature_increase",
  "parameters": {
    "temp_offset_c": 2.0,
    "rainfall_multiplier": 0.8
  },
  "num_simulations": 100,
  "horizon_days": 30
}
```

**Response:**
```json
{
  "scenario_id": "sc-abc123",
  "baseline": { ... },
  "perturbed": { ... },
  "comparison": { ... },
  "ensemble_stats": {
    "mean_temp_change": 2.1,
    "rainfall_change_pct": -18.5,
    "confidence_interval": [1.8, 2.4]
  }
}
```

### `GET /scenario/list`
List available scenario types and past simulations.

### `GET /scenario/compare`
Compare two or more scenario results.

---

## Risk Assessment Endpoints

### `GET /risk/assess`
Compute climate risk assessment for a location.

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `location_id` | string | Location identifier |

**Response:**
```json
{
  "location_id": "KA-BLR-001",
  "heat_risk": { "score": 72, "level": "HIGH", "factors": [...] },
  "flood_risk": { "score": 45, "level": "MODERATE", "factors": [...] },
  "drought_risk": { "score": 28, "level": "LOW", "factors": [...] },
  "composite_risk": { "score": 52, "level": "MODERATE" },
  "explanation": "...",
  "insights": [...]
}
```

---

## RAG / Knowledge Base Endpoints

### `POST /rag/query`
Query the knowledge base with a natural language question.

**Request Body:**
```json
{
  "query": "What are the monsoon patterns in Karnataka?",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "...",
  "sources": [
    { "document": "imd_weather_data.md", "chunk": "...", "score": 0.89 }
  ]
}
```

### `GET /rag/search`
Semantic search over indexed documents.

### `GET /rag/collections`
List available document collections.

### `POST /rag/index`
Index a new document into the knowledge base.

---

## Feedback Endpoints

### `POST /feedback`
Submit user feedback on predictions or system behavior.

**Request Body:**
```json
{
  "type": "forecast_accuracy",
  "location_id": "KA-BLR-001",
  "rating": 4,
  "comment": "Rainfall forecast was close to actual"
}
```

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "detail": "Description of the error",
  "error_code": "BAD_REQUEST",
  "timestamp": "2026-08-07T00:00:00Z"
}
```

| Status Code | Error Code | Description |
|---|---|---|
| 400 | `BAD_REQUEST` | Invalid request parameters |
| 404 | `NOT_FOUND` | Resource not found |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
