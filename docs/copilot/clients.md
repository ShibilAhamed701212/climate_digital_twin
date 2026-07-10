# Copilot Client Adapters

The `copilot/clients/` package contains five lightweight client classes that provide mock climate data. These are the legacy interfaces being migrated to Runtime provider adapters in Phase 4. No new code should depend on these clients directly.

## ForecastClient (`copilot/clients/forecast_client.py`)

Generates mock forecast data for a location over `days` days.

```python
from copilot.clients.forecast_client import ForecastClient

client = ForecastClient(base_url="http://forecast-engine:8006")
predictions = client.predict(location="Bangalore", days=3)

# Returns:
# [
#   {"date": "2025-06-15", "location": "Bangalore", "temperature": 28.5,
#    "humidity": 65, "precipitation_probability": 0.3},
#   {"date": "2025-06-16", "location": "Bangalore", "temperature": 29.0,
#    "humidity": 63, "precipitation_probability": 0.4},
#   ...
# ]
```

Temperature increments by 0.5°C per day, humidity decreases by 2% per day, precipitation probability increases by 0.1 per day.

## RiskClient (`copilot/clients/risk_client.py`)

Generates mock risk assessment scores for a location.

```python
from copilot.clients.risk_client import RiskClient

client = RiskClient(base_url="http://risk-engine:8003")
scores = client.assess(location="Bangalore", use_model_shap=True)

# Returns:
# {
#   "location": "Bangalore",
#   "heat": 0.45, "flood": 0.30, "drought": 0.25,
#   "composite": 0.35, "category": "moderate"
# }
```

## TwinClient (`copilot/clients/twin_client.py`)

Returns mock digital twin state data for a location.

```python
from copilot.clients.twin_client import TwinClient

client = TwinClient(base_url="http://twin-engine:8004")
state = client.get_current_state(location="Bangalore")

# Returns:
# {
#   "location": "Bangalore",
#   "temperature": 28.5, "humidity": 65,
#   "rainfall": 120.0, "soil_moisture": 0.42
# }
```

## RAGClient (`copilot/clients/rag_client.py`)

Simulates a semantic knowledge base search with mock results.

```python
from copilot.clients.rag_client import RAGClient

client = RAGClient(base_url="http://knowledge-engine:8001")
results = client.search(query="rainfall patterns in Karnataka", top_k=3)

# Returns:
# [
#   {"title": "Result 1 for: ...", "snippet": "Climate data relevant to ...",
#    "score": 0.95},
#   {"title": "Result 2 for: ...", "snippet": "...", "score": 0.85},
#   {"title": "Result 3 for: ...", "snippet": "...", "score": 0.75}
# ]
```

## ReportClient (`copilot/clients/report_client.py`)

Generates a mock structured climate report.

```python
from copilot.clients.report_client import ReportClient

client = ReportClient(base_url="http://report-engine:8005")
report = client.generate_report(location="Bangalore", report_type="summary")

# Returns:
# {
#   "location": "Bangalore",
#   "report_type": "summary",
#   "title": "Climate summary for Bangalore",
#   "findings": ["Temperature trends show...", "Rainfall variability...", ...],
#   "recommendations": ["Implement water conservation...", ...]
# }
```

## Migration Status

All clients currently return mock data. The Runtime provider adapters (`climate/providers/`) wrap these clients as migration wrappers. In Phase 4, the adapters will be replaced with real provider implementations, and these client classes will be removed.
