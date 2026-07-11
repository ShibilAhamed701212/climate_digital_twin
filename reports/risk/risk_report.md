# Risk Report

> **⚠️ Risk scores computed on synthetic data.** Not calibrated against real hazard events.

---

## Risk Scoring Engine

Four independent scoring modules, each producing a 0–100 score, aggregated into a composite:

```
Input (synthetic climate variables)
    │
    ├── HeatRisk       → score 0-100 (weight: 0.33)
    ├── FloodRisk      → score 0-100 (weight: 0.33)
    ├── DroughtRisk    → score 0-100 (weight: 0.34)
    │
    └── CompositeRisk  → weighted average (0-100)
```

---

## Heat Risk

| Component | Weight | Description |
|-----------|--------|-------------|
| Max temperature | 40% | How far above threshold |
| Consecutive hot days | 35% | Duration of heat event |
| Temperature anomaly | 25% | Deviation from baseline |

**Threshold:** 35°C (configurable from risk.yaml)

## Flood Risk

| Component | Weight | Description |
|-----------|--------|-------------|
| Rainfall intensity | 40% | Precipitation amount |
| Accumulation period | 35% | Multi-day accumulation |
| Uncertainty factor | 25% | Based on variability |

**Threshold:** 100mm/day (configurable)

## Drought Risk

| Component | Weight | Description |
|-----------|--------|-------------|
| Rainfall deficit | 40% | Below normal precipitation |
| Temperature increase | 30% | Exacerbating factor |
| Dry period duration | 30% | Consecutive dry days |

---

## Risk Categories

| Score Range | Category | Color |
|-------------|----------|-------|
| 0–20 | Very Low | Green |
| 21–40 | Low | Yellow |
| 41–60 | Moderate | Orange |
| 61–80 | High | Red |
| 81–100 | Severe | Dark Red |

---

## Configuration

Risk weights are configurable via `risk.yaml`:

```yaml
heat_risk:
  max_temp_weight: 0.40
  hot_days_weight: 0.35
  anomaly_weight: 0.25
  threshold: 35.0

flood_risk:
  intensity_weight: 0.40
  accumulation_weight: 0.35
  uncertainty_weight: 0.25
  threshold: 100.0

drought_risk:
  deficit_weight: 0.40
  temp_increase_weight: 0.30
  dry_period_weight: 0.30

composite:
  heat_weight: 0.33
  flood_weight: 0.33
  drought_weight: 0.34
```

---

## Limitations

1. **No real data calibration.** Risk thresholds chosen arbitrarily.
2. **No historical validation.** Scores have not been compared against actual hazard events.
3. **No spatial context.** Does not account for topography, drainage, or land use.
4. **No temporal dynamics.** Single-timestep assessment only (no trend analysis).
5. **No uncertainty bounds.** Single-point scores without confidence intervals.
