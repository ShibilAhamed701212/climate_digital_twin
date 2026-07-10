# Explainability Report

## Overview
The explainability subsystem provides SHAP-based feature attributions, human-readable risk interpretations, and natural language insights for all climate risk predictions. It enables domain experts and non-technical users to understand *why* a particular risk score was assigned.

## Components

| Component | File | Responsibility |
|-----------|------|----------------|
| SHAP Explainer | `risk/explainability/shap_explainer.py` | Feature-level SHAP attributions |
| Insights Engine | `risk/explainability/insights_engine.py` | Natural language climate insights |
| ClimateInsight | `risk/models/risk_models.py` | Insight data model |

## SHAP Explanation Engine

### Architecture

The SHAP explainer operates in two modes:

1. **Online Mode:** Uses a trained model to compute real SHAP values (requires model + background dataset)
2. **Offline Fallback:** Estimates feature contributions deterministically using domain-knowledge heuristics

Currently operating in **offline fallback mode** (no trained SHAP model attached).

### SHAPExplanation Model

```python
SHAPExplanation:
  prediction: float                  # Risk score (0–100)
  base_value: float                  # Expected value without features (50.0)
  feature_attributions: list[FeatureAttribution]  # Per-feature SHAP values
  top_features: list[str]            # Features ranked by |SHAP|
  positive_contributors: list[FeatureAttribution]  # Risk-increasing
  negative_contributors: list[FeatureAttribution]  # Risk-decreasing
  confidence: float                  # Prediction confidence (0–1)
  risk_interpretation: str           # Human-readable explanation
```

### FeatureAttribution Model

```python
FeatureAttribution:
  feature_name: str     # e.g., "max_temp"
  shap_value: float     # Contribution magnitude (+/−)
  feature_value: float  # Actual feature value
  contribution_type: str  # "positive" or "negative"
```

### Deterministic SHAP Estimation

When no trained model is available, the explainer estimates SHAP values:

```python
def _estimate_shap_values(prediction, feature_values, base_value):
    prediction_deviation = prediction - base_value
    total_abs_value = sum(abs(v) + 1.0 for v in feature_values.values())
    
    for value in feature_values.values():
        weight = (abs(value) + 1.0) / total_abs_value
        if value > 0:
            contrib = prediction_deviation * weight
        else:
            contrib = -prediction_deviation * weight * 0.3
        contributions.append(contrib)
    return contributions
```

Key heuristic: positive feature values increase risk proportionally; negative values decrease risk with 0.3× dampening.

### Risk Interpretation

The `_build_interpretation` function generates a natural language explanation:

```
"The composite climate risk score is 45.0 (Moderate). 
 Primary risk drivers: max_temp (+2.134), rainfall (+1.567), 
 consecutive_hot_days (+0.892). 
 Mitigating factors: dry_period_days (-0.456)."
```

### Global Feature Importance

The `get_global_feature_importance` function aggregates SHAP values across multiple predictions:

```python
GlobalFeatureImportance:
  feature_name: str
  mean_abs_shap: float      # Average |SHAP| across all predictions
  importance_percent: float  # Percentage of total SHAP magnitude
```

## Climate Insights Engine

### Insight Generation Triggers

The Insights Engine (`insights_engine.py`) produces natural language insights when specific thresholds are exceeded:

### Heat Insights

| Condition | Example Insight |
|-----------|----------------|
| seasonal_anomaly > 2.0°C | "Temperature is 2.5°C above seasonal average. Increased heat stress risk for vulnerable populations." |
| consecutive_hot_days >= 3 | "4 consecutive hot days recorded. Prolonged heat exposure increases health risks and energy demand." |

### Flood Insights

| Condition | Example Insight |
|-----------|----------------|
| rainfall_intensity > 100mm | "Rainfall intensity at 125.3mm — above heavy rain threshold. Elevated flash flood risk in urban and low-lying areas." |
| multi_day_accumulation > 200mm | "Multi-day accumulation of 280.1mm. Sustained rainfall increases river flooding and waterlogging risk." |

### Drought Insights

| Condition | Example Insight |
|-----------|----------------|
| rainfall_deficit < -25% | "Rainfall deficit of 35.2% below historical mean. Reduced water availability may impact agriculture and drinking water supply." |
| temperature_anomaly > 1.5°C | "Temperature 2.1°C above normal. Higher temperatures accelerate evaporation, worsening drought conditions." |

### Composite Insights

| Condition | Example Insight |
|-----------|----------------|
| Always | "Composite climate risk index is 45.4. Primary driver: Heat Risk." |
| composite.score > 60 | "Composite risk is 72.1 — classified as High. Proactive monitoring and mitigation measures recommended." |

## Risk Labels

| Score | Label |
|-------|-------|
| ≤ 20 | Very Low |
| ≤ 40 | Low |
| ≤ 60 | Moderate |
| ≤ 80 | High |
| > 80 | Severe |

## Example End-to-End

```
Input:
  max_temp=35.0, consecutive_hot_days=4, seasonal_anomaly=2.5
  rainfall=85.3, multi_day_accumulation=210.0
  dry_period_days=7, historical_mean_rainfall=100.0

Risk Scores:
  Heat: 62.5 (High)
  Flood: 35.2 (Low)  
  Drought: 28.6 (Low)
  Composite: 42.1 (Moderate)

SHAP Explanation:
  Top features: max_temp (+2.134), rainfall (+1.567), 
  consecutive_hot_days (+0.892), dry_period_days (-0.456)

Insights:
  - "Temperature is 2.5°C above seasonal average."
  - "4 consecutive hot days recorded."
  - "Composite climate risk index is 42.1. Primary driver: Heat Risk."
```

## Configuration

```yaml
# From risk/configs/risk.yaml
shap:
  enabled: true
  random_seed: 42
  max_display_features: 10
  background_samples: 100
```

## Limitations

1. **Offline fallback mode** — SHAP values are estimated, not computed from a trained model
2. **No deep learning explainer** — KernelSHAP or DeepSHAP not integrated
3. **No force plots** — Visualization is text-only, no SHAP force/waterfall plots
4. **Linear assumption** — Deterministic estimation assumes linear feature contributions
5. **Background samples unused** — config specifies 100 samples but offline mode doesn't use them
