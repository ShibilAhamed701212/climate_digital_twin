# Risk Assessment Report

## Overview
The Risk Engine computes climate risk scores for heat, flood, drought, and composite risks across Karnataka locations. It uses configurable weighted scoring models, SHAP-based explainability, and generates multi-format reports.

## Architecture

### Components

| Component | File | Responsibility |
|-----------|------|----------------|
| RiskEngine | `risk/engine/risk_engine.py` | Orchestrates risk computation, explanation, reporting |
| Heat Scoring | `risk/scoring.py:calculate_heat_risk` | Heat risk (max_temp, consecutive_hot_days, seasonal_anomaly) |
| Flood Scoring | `risk/scoring.py:calculate_flood_risk` | Flood risk (rainfall, multi_day_accumulation, forecast_uncertainty) |
| Drought Scoring | `risk/scoring.py:calculate_drought_risk` | Drought risk (rainfall_deficit, temperature_increase, dry_period_days) |
| Composite Scoring | `risk/scoring.py:calculate_composite_risk` | Weighted combination |
| SHAP Explainer | `risk/explainability/shap_explainer.py` | Feature attribution & interpretation |
| Insights Engine | `risk/explainability/insights_engine.py` | Natural language insights from risk scores |
| Report Generator | `risk/reports/report_generator.py` | Multi-format report output |
| Risk API | `risk/api/main.py` | REST API (7 endpoints) |
| Risk Contract | `risk/api/contract.py` | Abstract interface definition |

### API Endpoints (Risk Engine `:8003`)

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /risk/assess | Full risk assessment (all types) |
| POST | /risk/heat | Heat risk only |
| POST | /risk/flood | Flood risk only |
| POST | /risk/drought | Drought risk only |
| POST | /risk/composite | Composite risk only |
| POST | /risk/report | Full assessment + report generation |

## Risk Configuration

From `risk/configs/risk.yaml`:

### Score Categories

| Category | Range |
|----------|-------|
| Very Low | 0–20 |
| Low | 21–40 |
| Moderate | 41–60 |
| High | 61–80 |
| Severe | 81–100 |

### Heat Risk Weights

| Feature | Weight | Threshold |
|---------|--------|-----------|
| max_temperature | 0.40 | ≥35°C hot day |
| consecutive_hot_days | 0.35 | ≥3 consecutive |
| seasonal_anomaly | 0.25 | — |

### Flood Risk Weights

| Feature | Weight | Threshold |
|---------|--------|-----------|
| rainfall_intensity | 0.40 | ≥100mm heavy rain |
| multi_day_accumulation | 0.35 | 3-day window |
| forecast_uncertainty | 0.25 | — |

### Drought Risk Weights

| Feature | Weight | Threshold |
|---------|--------|-----------|
| rainfall_deficit | 0.40 | ≤-25% deficit |
| temperature_increase | 0.30 | — |
| dry_period_days | 0.30 | ≥15 days |

### Composite Risk Weights

| Component | Weight |
|-----------|--------|
| Heat | 0.33 |
| Flood | 0.33 |
| Drought | 0.34 |

### SHAP Configuration

| Parameter | Value |
|-----------|-------|
| enabled | true |
| random_seed | 42 |
| max_display_features | 10 |
| background_samples | 100 |

## Risk Models

### HeatRiskScore

```python
HeatRiskScore:
  score: float (0–100)
  max_temp: float
  consecutive_hot_days: int
  seasonal_anomaly: float
  category: str
```

### FloodRiskScore

```python
FloodRiskScore:
  score: float (0–100)
  rainfall_intensity: float
  multi_day_accumulation: float
  forecast_uncertainty: float
  category: str
```

### DroughtRiskScore

```python
DroughtRiskScore:
  score: float (0–100)
  rainfall_deficit_percent: float
  temperature_anomaly: float
  dry_period_days: int
  category: str
```

### CompositeRiskScore

```python
CompositeRiskScore:
  score: float (0–100)
  heat_score: float
  flood_score: float
  drought_score: float
  category: str
```

### RiskReport

```python
RiskReport:
  location_id: str
  district: str
  heat_risk: HeatRiskScore
  flood_risk: FloodRiskScore
  drought_risk: DroughtRiskScore
  composite_risk: CompositeRiskScore
  explanation: SHAPExplanation
  insights: list[ClimateInsight]
  raw_data: dict
```

## SHAP Explainability

The SHAP explainer (`shap_explainer.py`) generates feature attributions using deterministic estimation when no trained model is available.

### Score Interpretation

```python
def _build_interpretation(prediction, category, top_features):
    "The composite climate risk score is 45.0 (Moderate). \
     Primary risk drivers: max_temp (+2.134), rainfall (+1.567). \
     Mitigating factors: dry_period_days (-0.456)."
```

## Climate Insights

The Insights Engine (`insights_engine.py`) generates human-readable insights from risk scores:

| Condition | Insight |
|-----------|---------|
| seasonal_anomaly > 2.0°C | "Temperature is X°C above seasonal average" |
| consecutive_hot_days >= 3 | "X consecutive hot days recorded" |
| rainfall_intensity > 100mm | "Rainfall intensity at Xmm — above heavy rain threshold" |
| multi_day_accumulation > 200mm | "Multi-day accumulation of Xmm" |
| rainfall_deficit < -25% | "Rainfall deficit of X% below historical mean" |
| composite.score > 60 | "Composite risk is X — classified as High/Severe" |

## Example Assessment

```python
POST /risk/assess
{
  "location_id": "KA-BLR-001",
  "district": "Bangalore Urban",
  "max_temp": 35.0,
  "min_temp": 22.0,
  "rainfall": 85.3,
  "historical_mean_rainfall": 100.0,
  "historical_mean_temp": 28.0,
  "consecutive_hot_days": 4,
  "dry_period_days": 7,
  "seasonal_anomaly": 2.5,
  "forecast_uncertainty": 0.15,
  "prediction_confidence": 0.87
}

# Response (abbreviated)
{
  "heat_risk": {"score": 62.5, "category": "High"},
  "flood_risk": {"score": 28.4, "category": "Low"},
  "drought_risk": {"score": 45.2, "category": "Moderate"},
  "composite_risk": {"score": 45.4, "category": "Moderate"},
  "insights": [...]
}
```

## Report Generation

| Format | Path | Description |
|--------|------|-------------|
| JSON | risk/outputs/{location_id}_risk_report.json | Machine-readable |
| Markdown | risk/outputs/{location_id}_risk_report.md | Human-readable |
