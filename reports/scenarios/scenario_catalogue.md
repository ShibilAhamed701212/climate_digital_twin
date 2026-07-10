# Scenario Catalogue

## Preset Scenarios

### Temperature Scenarios

| ID | Name | Delta | Description |
|----|------|-------|-------------|
| `temp_plus_1` | Temperature +1°C | +1.0°C | Moderate warming scenario |
| `temp_plus_2` | Temperature +2°C | +2.0°C | Paris Agreement threshold scenario |
| `temp_minus_1` | Temperature -1°C | -1.0°C | Cooling / La Niña scenario |

### Rainfall Scenarios

| ID | Name | Change | Description |
|----|------|--------|-------------|
| `rain_plus_10` | Rainfall +10% | +10% | Moderate wet scenario |
| `rain_plus_40` | Rainfall +40% | +40% | Extreme wet / flood-prone scenario |
| `rain_minus_25` | Rainfall -25% | -25% | Moderate drought scenario |

### Monsoon Scenarios

| ID | Name | Delay | Intensity Change | Description |
|----|------|-------|-----------------|-------------|
| `monsoon_delayed_15` | Monsoon Delayed 15 Days | +15 days | -20% | Late onset with weaker monsoon |
| `monsoon_early_7` | Monsoon Early 7 Days | -7 days | 0% | Early onset scenario |

### Extreme Event Scenarios

| ID | Name | Type | Parameters | Duration |
|----|------|------|-----------|----------|
| `heatwave` | Extreme Heat Wave | heatwave | +5.0°C | 7 days |
| `flood` | Flood Scenario | flood | +200% rainfall | 5 days |
| `drought` | Drought Condition | drought | -80% rainfall | 30 days |

## Scenario Ranges (Configurable)

### Temperature

| Property | Min | Max | Step |
|----------|-----|-----|------|
| Delta | -5.0°C | +5.0°C | 0.5°C |

### Rainfall

| Property | Min | Max | Step |
|----------|-----|-----|------|
| Percent Change | -100% | +500% | 5% |

### Monsoon

| Property | Max | 
|----------|-----|
| Delay | 30 days |
| Advance | 15 days |
| Intensity Reduction | 0–50% |

## Use Cases by Stakeholder

### Agricultural Planners
| Scenario | Use |
|----------|-----|
| rain_minus_25 | Drought preparedness planning |
| monsoon_delayed_15 | Sowing date adjustment |
| temp_plus_2 | Crop variety selection |

### Urban Infrastructure
| Scenario | Use |
|----------|-----|
| rain_plus_40 | Drainage capacity planning |
| heatwave | Heat action plan activation |
| flood | Flood mapping and evacuation planning |

### Water Resource Managers
| Scenario | Use |
|----------|-----|
| drought | Reservoir level planning |
| rain_minus_25 | Water allocation strategy |
| monsoon_early_7 | Dam operation schedule |

### Disaster Management
| Scenario | Use |
|----------|-----|
| flood | Early warning system trigger |
| heatwave | Health advisory activation |
| drought | Relief deployment planning |

## Combined Scenarios

Combined scenarios apply multiple sub-scenarios sequentially:

```json
{
  "scenario_type": "combined",
  "parameters": {
    "scenarios": [
      {"scenario_type": "temperature", "parameters": {"temperature_delta": 2.0}},
      {"scenario_type": "rainfall", "parameters": {"rainfall_change_pct": -25.0}}
    ]
  }
}
```

Max 5 sub-scenarios per combined scenario.
