# Scenario Report

> **⚠️ Scenario engine modifies synthetic baseline data.** Results are deterministic perturbations of fake data.

---

## Scenario Engine Architecture

```
Baseline State (synthetic)
        │
        ▼
  Scenario Type Selection
        │
        ├── TemperatureScenario    → add/subtract °C
        ├── RainfallScenario       → multiply/percent change
        ├── MonsoonScenario        → onset delay + intensity change
        ├── ExtremeEventScenario   → heatwave/coldwave/flood/drought
        └── CombinedScenario        → multiple perturbations simultaneously
        │
        ▼
  Scenario Parameters
        │
        ▼
  Deterministic Execution (< 3 seconds)
        │
        ▼
  Physics Validation (rainfall >= 0, temp bounds)
        │
        ▼
  Result State (synthetic delta)
```

---

## Scenario Types

| Type | Parameters | Execution | Status |
|------|-----------|-----------|--------|
| Temperature | Delta in °C, apply to t2m_max/t2m_min | O(n) per location | ✅ Working |
| Rainfall | Multiplier or percentage change | O(n) per location | ✅ Working |
| Monsoon | Onset delay in days, intensity factor | Timeline shift | ✅ Working |
| Extreme Event | Type (heatwave/coldwave/flood/drought), intensity | Point perturbation | ✅ Working |
| Combined | Multiple scenario operations | Sequential composition | ✅ Working |

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Single scenario, single location | <100ms | Deterministic |
| Single scenario, all 15 districts | <500ms | O(n) in districts |
| Combined scenario, all districts | <3s | Multiple operations |
| Output formatting (JSON/CSV/MD) | <10ms | |

---

## Outputs

| Format | Description |
|--------|-------------|
| JSON | Structured scenario results with deltas |
| CSV | Table of before/after values per location |
| Markdown | Human-readable scenario report |

---

## Scenario Catalogue

See `scenario_catalogue.md` for the full list of 11 preset scenarios.

---

## Limitations

1. **Baseline is synthetic.** Scenario results are deltas from fake data.
2. **No calibration.** Scenario magnitudes chosen arbitrarily, not from climate science literature.
3. **No spatial correlation.** Each location perturbed independently.
4. **No temporal dynamics.** Scenarios apply to a single timestep baseline.
5. **No uncertainty quantification.** All results are single-point deterministic.
