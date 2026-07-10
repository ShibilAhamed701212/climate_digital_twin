# Risk Maps Report

## Overview
Risk maps visualize heat, flood, drought, and composite climate risk scores across Karnataka's districts. These maps enable disaster management authorities and agricultural planners to identify high-risk zones and allocate resources proactively.

## Risk Scoring Methodology

### Heat Risk
Heat risk is computed from three factors with configurable weights:

| Factor | Weight | Calculation |
|--------|--------|-------------|
| Max Temperature | 0.40 | Normalized against 35°C threshold (max_temp / 45) × 100 |
| Consecutive Hot Days | 0.35 | (min(days, 14) / 14) × 100 |
| Seasonal Anomaly | 0.25 | (anomaly / 5) × 100, capped |

**Formula:** `score = min(100, sum(factor × weight for each factor))`

### Flood Risk

| Factor | Weight | Calculation |
|--------|--------|-------------|
| Rainfall Intensity | 0.40 | (rainfall / 200) × 100, capped |
| Multi-day Accumulation | 0.35 | (accumulation / 500) × 100, capped |
| Forecast Uncertainty | 0.25 | uncertainty × 100 |

**Formula:** `score = min(100, sum(factor × weight for each factor))`

### Drought Risk

| Factor | Weight | Calculation |
|--------|--------|-------------|
| Rainfall Deficit | 0.40 | abs(deficit%) / 100 × 100, capped |
| Temperature Increase | 0.30 | (anomaly / 5) × 100, capped |
| Dry Period Days | 0.30 | (min(days, 60) / 60) × 100 |

**Formula:** `score = min(100, sum(factor × weight for each factor))`

### Composite Risk

```python
composite = heat * 0.33 + flood * 0.33 + drought * 0.34
```

## Risk Categories

| Category | Range | Color | Action |
|----------|-------|-------|--------|
| Very Low | 0–20 | Green | Normal monitoring |
| Low | 21–40 | Yellow | Routine awareness |
| Moderate | 41–60 | Orange | Preparedness actions |
| High | 61–80 | Red | Warning issuance |
| Severe | 81–100 | Dark Red | Emergency response |

## Karnataka District Risk Zones

### Heat Risk Vulnerability

| District | Typical Summer Max Temp | Heat Risk Level | Primary Concern |
|----------|------------------------|----------------|-----------------|
| Bellary | 38–42°C | High to Severe | Heat stroke, crop failure |
| Raichur | 37–41°C | High | Water scarcity |
| Gulbarga | 36–40°C | High | Livestock stress |
| Bangalore Urban | 32–36°C | Moderate | Urban heat island |
| Dakshina Kannada | 30–34°C | Low | Coastal moderation |

### Flood Risk Vulnerability

| District | Avg Monsoon Rainfall | Topography | Flood Risk |
|----------|---------------------|------------|------------|
| Udupi | 4,000mm | Coastal | High |
| Dakshina Kannada | 3,800mm | Coastal | High |
| Uttara Kannada | 2,800mm | Western Ghats | Moderate to High |
| Shimoga | 1,800mm | Inland | Moderate |
| Bangalore Urban | 900mm | Plateau | Low |

### Drought Risk Vulnerability

| District | Avg Rainfall | Drought Risk | Primary Season |
|----------|-------------|--------------|----------------|
| Bellary | 600mm | High | Rabi |
| Raichur | 650mm | High | Rabi |
| Gulbarga | 700mm | Moderate to High | Rabi |
| Chitradurga | 750mm | Moderate | Kharif |
| Mandya | 800mm | Moderate | Kharif |

## Drought Severity Classification

| Condition | Deficit | Drought Classification |
|-----------|---------|----------------------|
| No Deficit | ≥ 0% | Normal |
| Mild | -1% to -25% | Watch |
| Moderate | -26% to -50% | Alert |
| Severe | -51% to -75% | Warning |
| Extreme | < -75% | Emergency |

## Example Risk Map Output

For a hypothetical assessment on 2026-06-29 with recent IMD data:

| District | Heat | Flood | Drought | Composite | Dominant Risk |
|----------|------|-------|---------|-----------|---------------|
| Bangalore Urban | 35 | 22 | 30 | 29 | Heat |
| Bellary | 78 | 5 | 72 | 52 | Heat/Drought |
| Udupi | 18 | 72 | 15 | 35 | Flood |
| Raichur | 72 | 8 | 68 | 49 | Heat/Drought |
| Dakshina Kannada | 22 | 68 | 12 | 34 | Flood |
| Gulbarga | 65 | 10 | 55 | 43 | Heat/Drought |
| Shimoga | 28 | 42 | 35 | 35 | Flood |
| Chitradurga | 55 | 15 | 60 | 43 | Drought |

## Composite Risk Heatmap (Text Representation)

```
                      Heat Risk
                  Low   Mod   High  Sev
               ┌─────┬─────┬─────┬─────┐
          Low  │  ██  │  ██  │  ██  │     │  Low overall
               ├─────┼─────┼─────┼─────┤
Flood   Mod    │  ██  │  ██  │  ██  │     │  Moderate concern
               ├─────┼─────┼─────┼─────┤
Risk    High   │     │  ██  │  ██  │     │  High risk zone
               ├─────┼─────┼─────┼─────┤
        Sev    │     │     │  ██  │  ██  │  Emergency

██ = Actual districts mapped to combined risk
```

## Recommendations by Risk Profile

| Composite Profile | Recommended Actions |
|-------------------|---------------------|
| Heat-Dominant | Heat action plans, cooling centers, power grid reinforcement |
| Flood-Dominant | Drainage maintenance, early warning systems, evacuation routes |
| Drought-Dominant | Water conservation, reservoir management, alternate crop planning |
| Balanced Moderate | Integrated climate resilience planning |
| High/Composite >60 | Multi-hazard disaster preparedness, insurance activation |

## Integration with Twin

Risk scores are pushed back to the Digital Twin state:

```
RiskEngine.assess_all()
  → returns RiskReport
  → DigitalTwinEngine.update_risk_score(location_id, composite_score)
  → TwinService.update_risk_score()
    → StateManager.create_version(entity with updated risk_score)
    → ParquetRepository.save_version(version)
    → EventBus.publish(RiskUpdated event)
```

## Visualization Points

Each risk assessment endpoint returns scores compatible with:
- Streamlit dashboard color-coded maps (Folium)
- Time-series risk trend charts (Plotly)
- District-level risk comparison tables
- Radar charts for multi-risk profiles
