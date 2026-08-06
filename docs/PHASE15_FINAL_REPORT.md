# Phase 15 Final Report — Scientific Certification

Date: 2026-08-02
Project: Climate Digital Twin — ISRO BAH 2026 Challenge 5

---

## Final Verdict

**CERTIFIED FOR SCIENTIFIC RESEARCH USE**

The Climate Digital Twin is a real-data climate intelligence prototype with verified observation ingestion, physical water-balance simulation, basic hazard threshold scoring, and spatial multi-grid capability. It is NOT a validated operational prediction system. It is an honest research platform with strong provenance engineering and transparent scientific limitations.

---

## 1. Forecast Validation

### Production Model: Persistence (yesterday = today)

| Target | RMSE | R² | Skill vs Climatology |
|--------|------|-----|---------------------|
| Tmax | 1.20 °C | 0.851 | +0.316 |
| Tmin | 0.91 °C | 0.882 | +0.636 |
| Rainfall | 3.47 mm | -0.525 | -0.109 |

**Scientific finding:** No ML model (LSTM, MLP, NHITS, NBEATS) beats persistence on temperature. Rainfall is fundamentally unpredictable at daily scale from local autocorrelation alone. This is consistent with published meteorological literature — daily convective rainfall in monsoon climates is governed by large-scale dynamics, not local persistence.

### Validation Method
- 1,827-day Open-Meteo Bengaluru dataset
- Chronological 70/15/15 split, no data leakage
- Baselines: persistence (RMSE 1.20), climatology (1.59)
- Neural models: LSTM (1.22), MLP (1.50)
- GPU benchmarking: NHITS trained, prediction alignment debugged

---

## 2. Hazard Validation

### Supported Hazards

| Hazard | Method | 1827-day Backtest |
|--------|--------|------------------|
| HEAT | 35°C threshold, linear 4x scaling | 74 events (4.1%), all LOW. Max: 18.0 at 39.5°C |
| HEAVY_RAIN | 100mm threshold, linear scaling | 0 SEVERE events in OM Bengaluru. Max: 69.6mm, MODERATE |
| DRYNESS | 15-day threshold, rainfall deficit | 21 spells >=10 days. Longest: 93 days (Jan-Apr 2024) |

### Limitations
- Hazard scores are deterministic threshold mappings, not calibrated event probabilities
- No exposure/vulnerability models (no casualties, economic damage, infrastructure impact)
- FLOOD, DROUGHT, STORM, WILDFIRE are explicitly UNSUPPORTED per risk_config.yaml
- Heat scoring is a generic single-day threshold, not a validated heatwave model
- Only one hazard returned per assessment (highest-scoring)

### Validation Against Historical Events
- 2022-08-18 extreme rainfall (266.32mm): SEVERE at nearest NASA POWER grid cell (12.5°N, 78.0°E). Not captured in Open-Meteo Bengaluru point record.
- 2016-04-24 extreme heat (42.42°C): LOW at grid cell. The 35°C threshold × 4x scaling means even record temperatures can't reach MODERATE for Bengaluru.

---

## 3. Penman-Monteith Validation

### FAO-56 Example 18

| Method | Computed | Expected | Error |
|--------|----------|----------|-------|
| Penman-Monteith | 4.88 mm/day | 5.31 mm/day | 8% |
| Hargreaves-Samani | 5.03 | 5.03 | 0% |

The 8% PM discrepancy is attributed to simplified RH handling (mean daily vs proper Tdew/RHmax-RHmin per FAO-56 Eq 17-19).

### Bengaluru Monsoon Comparison

| Method | ET0 (mm/day) | Note |
|--------|-------------|------|
| Hargreaves-Samani | 4.81 | Overestimates — ignores >80% monsoon RH |
| Penman-Monteith | 4.23 | Physically correct — VPD accounts for monsoon humidity |

PM reduces monsoon ET estimate by 12% — consistent with known HS overestimation bias.

### Limitation
No independent ET reference data (GLEAM, flux tower, lysimeter) for Bengaluru. PM validated against FAO-56 reference case only, not against local measurements.

---

## 4. Spatial Validation

### Karnataka Grid Twin

| Property | Value |
|----------|-------|
| Grid cells | 651 (31 × 21, 0.25°) |
| Coverage | 11.0-18.5°N, 74.0-79.0°E |
| Data | ERA5 2021-2023, 36 months |
| Processing speed | 1.0 ms/cell (vectorized xarray) |
| Temperature range | -9.8°C (Himalayas) to 38.1°C (desert) for India |

### Interpolation
- Nearest-neighbor: operational
- IDW (power=2, n=4): operational with source-cell provenance
- Bilinear/Kriging: architecture ready

### Limitation
No independent station data (IMD ground stations) to validate the ERA5 grid against point observations. The grid cells are reanalysis values, not ground-truth measurements.

---

## 5. Uncertainty Validation

### Conformal Prediction

| Property | Status |
|----------|--------|
| Algorithm | Split conformal prediction (Vovk et al. 2005) |
| Coverage guarantee | Marginal >= 1-alpha |
| Implementation | `climatedt/simulation/processes/uncertainty.py` |
| ForecastWithUncertainty model | `climatedt/forecast/uncertainty_models.py` |
| Piped to production API | NOT YET |

### Limitation
Conformal prediction is code-complete but not yet integrated into the production forecast pipeline. Prediction intervals are not exposed through the API or dashboard.

---

## 6. Scientific Stress Tests

### Historical Replay (2021-2026 Bengaluru)

- Mass balance: exact 0.0mm residual across 1737 simulation steps
- Storage bounds: 0-150mm enforced correctly
- Seasonal cycle: monsoon peaks, dry-season depletion tracked correctly
- 2022-08-18 extreme event: correctly detected at NASA POWER grid cell

### Provider Cross-Validation

| Variable | Open-Meteo vs NASA POWER | Agreement |
|----------|------------------------|-----------|
| Tmax | Bias -2.01°C (OM colder) | r=0.858 |
| Tmin | Bias -1.11°C (OM colder) | r=0.923 |
| Rainfall | Bias -0.28mm | r=0.325 |

The 2°C Tmax bias means the Twin's "true" temperature depends on which REAL provider is chosen. This is a fundamental data quality limitation, not a software bug.

---

## 7. Production Audit

| System | Status |
|--------|--------|
| Observation Pipeline | OPERATIONAL (Open-Meteo, ERA5, NASA POWER) |
| Twin Synchronization | OPERATIONAL (4-layer authenticity guard) |
| Forecast Pipeline | OPERATIONAL (persistence production model) |
| Risk Engine | OPERATIONAL (multi-hazard, config-driven thresholds) |
| Scenario Engine | OPERATIONAL (deterministic, SCENARIO-isolated) |
| Coupled Simulation | OPERATIONAL (mass-balanced, SIMULATED-authenticity) |
| Provenance | OPERATIONAL (full chain traceable) |
| Integrity Scanner | OPERATIONAL (REAL-store contamination detection) |
| Dashboard | OPERATIONAL (9 pages, terminology corrected) |
| API | OPERATIONAL (deprecated aliases maintained) |
| Copilot | OPERATIONAL (Qwen3:4b via Ollama) |
| Docker | OPERATIONAL (multi-service compose) |
| GPU | OPERATIONAL (GTX 1650, CUDA 12.1, torch 2.5.1+cu121) |

### Remaining Production Gaps

| Gap | Severity |
|-----|----------|
| No service authentication (all services exposed) | HIGH |
| No rate limiting | MEDIUM |
| No HTTPS/TLS | MEDIUM |
| NeuralForecast benchmark incomplete (API issue) | LOW |
| Conformal not piped to API | LOW |

---

## 8. Test Results

| Suite | Passed |
|-------|--------|
| Phase 4-7 targeted (hazard, scenario, simulation, integrity) | 152 |
| Phase 7 replay | 11 |
| Copilot (Ollama) | 21 |
| Dashboard | 209 |
| Copilot tools | 100 |
| Spatial (14C) | VERIFIED |
| ERA5 pipeline (48 months, 0 failures) | VERIFIED |
| **Total targeted** | **~500+** |

Full 2508-test suite confirmed clean on multiple runs.

---

## 9. Architecture Integrity

| Phase | Status |
|-------|--------|
| Phase 1-2 (data, twin) | PRESERVED |
| Phase 3 (forecast) | PRESERVED |
| Phase 4 (hazard) | EXTENDED (multi-hazard, config-driven) |
| Phase 5 (scenario) | PRESERVED |
| Phase 6 (production) | PRESERVED |
| Phase 7 (simulation) | EXTENDED (PM, humidity/wind/radiation) |
| Phase 8-9C (audit/fix/certify) | COMPLETED |
| Phase 10-12 (scientific upgrade) | COMPLETED |
| Phase 13-13.2 (forecast benchmark) | COMPLETED |
| Phase 14-14C (spatial twin) | COMPLETED |

Zero architectural regressions. All new code is additive within `climatedt/` package.

---

## 10. Scientific Scorecard

| Category | Score | Justification |
|----------|-------|---------------|
| Software Engineering | 85/100 | Clean architecture, deterministic engine, comprehensive tests |
| Data Authenticity | 90/100 | SHA-256 manifests, strict REAL gates, cross-provider disagreement unresolved |
| Forecast Validity | 25/100 | Persistence beats ML; rainfall R² negative; no UQ in production |
| Twin Fidelity | 80/100 | Core fields exact; minor provenance losses fixed |
| Simulation Validity | 40/100 | Equations reference-verified; zero empirical validation |
| Hazard Validation | 40/100 | Threshold rules backtested; uncalibrated; broken confidence fixed |
| Spatial Capability | 60/100 | 651-cell grid operational; no independent spatial validation |
| Provenance | 85/100 | Full chain traceable; audit-ready |
| Production Readiness | 55/100 | No auth, no TLS, no rate limiting; GPU working |
| **Overall** | **62/100** | A climate intelligence prototype with strong engineering |

---

## 11. What the Project CAN Claim

"A real-data climate intelligence prototype with verified observation ingestion (Open-Meteo, ERA5, NASA POWER), physical water-balance simulation (Hargreaves-Samani/Penman-Monteith ET, SCS-CN runoff, bucket storage, SPEI drought index), basic hazard threshold scoring, and 651-cell spatial Karnataka grid. Data authenticity is enforced through SHA-256 manifests and REAL-only gates. The forecast model (persistence) is simple but scientifically honest. The system is well-tested (500+ tests) with full provenance traceability."

## 12. What the Project CANNOT Claim

- NOT a validated operational prediction system (forecasts don't beat persistence)
- NOT a calibrated hydrological model (CN=70 uncalibrated, no gauge data)
- NOT a validated flood/drought/heatwave prediction system
- NOT an India-wide climate twin (single-location + one-state grid)
- NOT a physics-complete Earth-system twin (missing atmosphere, groundwater, vegetation)
- NOT production-secure (no auth, no TLS)

---

*Certified: 2026-08-02 | Phase 15 — Final Scientific Certification*
