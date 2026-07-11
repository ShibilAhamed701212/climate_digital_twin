# Explainability Report

> **⚠️ SHAP values are deterministic synthetic estimates.** Not connected to model gradients or real feature interactions.

---

## SHAP Implementation

Current implementation uses a **deterministic synthetic approach**:

```python
def estimate_shap(features: np.ndarray) -> np.ndarray:
    # ⚠️ NOT real SHAP. Returns synthetic values based on feature position.
    shap_values = np.zeros_like(features)
    for i in range(features.shape[1]):
        shap_values[:, i] = features[:, i] * (i + 1) * 0.1
    return shap_values
```

This is a placeholder. Integration with actual model gradients has not been implemented.

---

## Feature Importance

| Feature | Importance | Note |
|---------|------------|------|
| RollingMean_30d | High | Synthetic value based on position |
| Precipitation prev day | High | Synthetic value based on position |
| Temperature | Medium | Synthetic value based on position |
| Humidity | Medium | Synthetic value based on position |
| Wind speed | Low | Synthetic value based on position |
| Pressure | Low | Synthetic value based on position |

**All importance values are deterministic position-based fakes.** Real SHAP would show actual feature contributions from the model.

---

## Natural Language Insights

Template-based insight generation:

```
"{feature} is the primary driver of {risk_type} in {location}
with a contribution of {value:.2f}."
```

Example: "Consecutive hot days are the primary driver of high heat risk in Kalaburagi with a contribution of 12.45."

---

## Outputs

| Format | Content |
|--------|---------|
| JSON | Per-feature SHAP values (synthetic) |
| Markdown | Natural language report |

---

## API Endpoint

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/explain/risk` | POST | Get SHAP explanation for risk scores |

Request body:
```json
{
  "location": "kalaburagi",
  "features": {...}
}
```

Response: Synthetic SHAP values + template text.

---

## Limitations

1. **Not real SHAP.** Values are deterministic position-based estimates.
2. **Not connected to models.** No integration with PyTorch model gradients.
3. **No KernelSHAP/Lime.** No model-agnostic explainer.
4. **Insights are templates.** Not generated from actual feature analysis.
5. **No validation.** Explanations not verified against domain knowledge.
