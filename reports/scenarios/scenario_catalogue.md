# Scenario Catalogue

> **11 preset scenarios for climate perturbation simulation.**  
> ⚠️ All results are synthetic deltas from synthetic baselines.

---

## Temperature Scenarios

| ID | Name | Parameter | Description |
|----|------|-----------|-------------|
| T1 | +1°C Warming | delta=+1.0 | Moderate temperature increase |
| T2 | +2°C Warming | delta=+2.0 | Significant temperature increase |
| T3 | +3°C Warming | delta=+3.0 | Extreme temperature increase |
| T4 | -1°C Cooling | delta=-1.0 | Moderate temperature decrease |
| T5 | -2°C Cooling | delta=-2.0 | Significant temperature decrease |

## Rainfall Scenarios

| ID | Name | Parameter | Description |
|----|------|-----------|-------------|
| R1 | +10% Rainfall | multiplier=1.10 | Slight rainfall increase |
| R2 | +25% Rainfall | multiplier=1.25 | Moderate rainfall increase |
| R3 | +40% Rainfall | multiplier=1.40 | Extreme rainfall increase |
| R4 | -10% Rainfall | multiplier=0.90 | Slight rainfall decrease |
| R5 | -25% Rainfall | multiplier=0.75 | Moderate rainfall decrease |
| R6 | -40% Rainfall | multiplier=0.60 | Extreme rainfall decrease |

---

## Monsoon Scenario

| ID | Name | Parameters | Description |
|----|------|-----------|-------------|
| M1 | Delayed Monsoon | onset_delay=15, intensity=0.8 | 15-day delay with 80% intensity |

---

## Extreme Event Scenarios

| ID | Name | Parameters | Description |
|----|------|-----------|-------------|
| E1 | Heatwave | intensity=0.8, duration=5 | 5-day heatwave (temp +4°C) |
| E2 | Coldwave | intensity=0.7, duration=5 | 5-day coldwave (temp -5°C) |
| E3 | Heavy Flood | intensity=0.9, duration=3 | 3-day flood (rainfall x3) |
| E4 | Severe Drought | intensity=0.8, duration=30 | 30-day drought (rainfall x0.1) |

---

## Combined Scenarios

| ID | Name | Composition | Description |
|----|------|-------------|-------------|
| C1 | Hot + Dry | T2 (+2°C) + R5 (-25%) | Climate change baseline scenario |
| C2 | Wet + Warm | T1 (+1°C) + R2 (+25%) | Moderate combined change |
| C3 | Extreme | T3 (+3°C) + R6 (-40%) | Worst-case warming + drying |

---

## Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| delta | float | -5.0 to +5.0 | Temperature change in °C |
| multiplier | float | 0.1 to 3.0 | Rainfall scaling factor |
| intensity | float | 0.0 to 1.0 | Event severity |
| duration | int | 1–30 | Event duration in days |
| onset_delay | int | 0–30 | Monsoon onset delay in days |

---

## Notes

- All scenario parameters are arbitrary choices for demo purposes
- Not calibrated against climate model projections
- Results are deterministic: same input → same output
- Physics constraints (rainfall >= 0) enforced automatically
