# Risk Assessment Engine

## Overview

The **Risk Assessment Engine** (`risk/`) evaluates climate hazard vulnerabilities for districts and locations across India. It aggregates meteorological indicators, forecast trends, and historical baseline context to generate risk scores (0–100) and actionable alerts for **Heat**, **Flood**, and **Drought** events.

---

## Risk Categories & Calculation Methodology

### 1. Heat Risk (`risk/scoring/heat_risk.py`)
Calculates heatwave vulnerability based on:
- Maximum temperature exceedance above local thresholds (e.g., $>35^\circ C$).
- Duration of consecutive hot days.
- Seasonal anomaly magnitude relative to historical climatology.

### 2. Flood Risk (`risk/scoring/flood_risk.py`)
Assesses heavy rainfall and inundation hazard based on:
- Single-day precipitation intensity ($mm/day$).
- Multi-day cumulative rainfall accumulation (3-day and 7-day windows).
- Short-term forecast uncertainty and soil saturation levels.

### 3. Drought Risk (`risk/scoring/drought_risk.py`)
Evaluates agricultural and meteorological drought conditions based on:
- Percentage rainfall deficit relative to long-term monthly averages.
- Extended dry spell duration (consecutive days with $<2.5mm$ rain).
- Temperature-driven atmospheric evaporative demand.

### 4. Composite Risk (`risk/scoring/composite_risk.py`)
Integrates individual hazard scores into a unified risk index:
$$R_{composite} = w_{heat} R_{heat} + w_{flood} R_{flood} + w_{drought} R_{drought}$$
Default weights can be customized via `config/risk_config.yaml`.

---

## Risk Severity Levels

| Score Range | Risk Level | Description | Recommended Action |
|---|---|---|---|
| **0 – 25** | `LOW` (Green) | Normal climatic conditions | Regular monitoring |
| **26 – 50** | `MODERATE` (Yellow) | Elevated seasonal variation | Advisory notices |
| **51 – 75** | `HIGH` (Orange) | Severe hazard threshold approaching | Prepare emergency response |
| **76 – 100** | `CRITICAL` (Red) | Extreme climate threat | Immediate action required |

---

## Explainability & SHAP (`risk/explainability/`)

The risk engine incorporates SHAP (SHapley Additive exPlanations) to make every risk assessment transparent and interpretable:
- **`shap_explainer.py`**: Computes contribution weights for each input variable (e.g., $+15$ points from 3-day rainfall accumulation).
- **`insights_engine.py`**: Translates numerical SHAP values into natural-language explanation bullets for policymakers and domain non-experts.

---

## Quality Gates & Alerting (`risk/evaluation/`)

- **Alert Policy (`alert_policy.py`)**: Triggers automated alerts when risk levels transition to `HIGH` or `CRITICAL`.
- **Quality Gate (`quality_gate.py`)**: Validates input data completeness and prevents false alarms from sensor anomalies.
- **Hazard Store (`hazard_store.py`)**: Persists historical hazard evaluations for trend auditability.
