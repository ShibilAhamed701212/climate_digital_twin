# Phase 8 Final Report — Scientific Validation, Calibration & Skill Assessment

Date: 2026-08-01
Project: Climate Digital Twin — ISRO BAH 2026 Challenge 5

---

## 1. Executive Verdict

**PHASE 8 COMPLETE — CORE SYSTEM VALIDATED WITH IMPORTANT LIMITATIONS**

The system demonstrates working software engineering, strong data authenticity practices, and correct implementation of reference equations. However, scientific validation reveals fundamental gaps:

- Forecast models cannot be independently loaded or reproduced (environment-blocked)
- The two primary data providers (Open-Meteo, NASA POWER) disagree by ~2degC on Tmax and barely correlate on daily rainfall (r=0.325)
- Runoff and soil moisture have zero empirical validation against independent measurements
- The hazard evaluator is a threshold-rule engine producing deterministic scores, not calibrated event probabilities
- The dominant parameter (CN, Curve Number) is uncalibrated — CN=70 could reasonably be anywhere from 50 to 90

The project is correctly classified as a **real-data climate intelligence prototype** — not a validated prediction system.

---

## 2. Scientific Claims Register

| ID | Claim | Source | Evidence Found | Status |
|----|-------|--------|---------------|--------|
| C01 | Forecast LSTM predicts Tmax with RMSE 1.22 | Phase 3 | Cannot reproduce (torch broken); persistence baseline RMSE=1.21 | ENVIRONMENT_BLOCKED |
| C02 | Forecast LSTM predicts MinTemp with RMSE 0.91 | Phase 3 | Cannot reproduce; persistence RMSE=0.94 | ENVIRONMENT_BLOCKED |
| C03 | Forecast LSTM predicts Rainfall with R^2>0 | Phase 3 | Cannot reproduce; reported R^2=-0.04 acknowledges failure | ENVIRONMENT_BLOCKED |
| C04 | Hargreaves-Samani PET matches FAO-56 reference | Phase 7 | CODE-VERIFIED: ET0=5.03 (abs error 0.01) | REFERENCE_VERIFIED |
| C05 | PET approximates real ET | Phase 7 | No independent ET data found | INSUFFICIENT_DATA |
| C06 | SCS-CN runoff formula matches published example | Phase 7 | CODE-VERIFIED: Q=25.7 (abs error 0.2) | REFERENCE_VERIFIED |
| C07 | Runoff approximates real hydrological response | Phase 7 | No gauge/streamflow/reanalysis comparison | NOT_EMPIRICALLY_VALIDATED |
| C08 | Soil storage tracks wet/dry conditions | Phase 7 | Internal response tests only | PARTIALLY_VALIDATED |
| C09 | Soil moisture proxy matches reality | Phase 7 | No independent soil moisture data | INSUFFICIENT_DATA |
| C10 | SPEI drought index correctly implemented | Phase 7 | L-moment math verified manually; monsoon/dry discrimination correct | REFERENCE_VERIFIED |
| C11 | SPEI represents real drought conditions | Phase 7 | No independent drought index comparison | PARTIALLY_VALIDATED |
| C12 | HEAVY_RAIN hazard detects extreme rainfall | Phase 4 | Backtested on full 1827-day record; works as designed | PARTIALLY_VALIDATED |
| C13 | HEAT hazard detects dangerous temperatures | Phase 4 | Backtested; 74 events, all LOW; scoring is generic threshold rule | PARTIALLY_VALIDATED |
| C14 | DRYNESS hazard detects dry periods | Phase 4 | Backtested; 21 spells >= 10 days work correctly | PARTIALLY_VALIDATED |
| C15 | HEAT is "agriculturally calibrated" | Phase 4 | FALSE — generic 35degC threshold with no crop/region factors | FAILED_VALIDATION |
| C16 | Twin synchronization is lossless | Phase 4/6 | Core fields exact; optional fields fall to prior values when None | PARTIALLY_VALIDATED |
| C17 | Twin provenance preserved | Phase 6 | 4 fields stored; twin_version lost (set to entity_id) | PARTIALLY_VALIDATED |
| C18 | No SIMULATED in REAL stores | Phase 6/7 | VERIFIED: grep returns 0, file listings identical | VALIDATED |
| C19 | Deterministic simulation engine | Phase 7 | VERIFIED: same forcing -> same output | VALIDATED |
| C20 | Mass balance exact | Phase 7 | VERIFIED: residual=0.0mm per-step and per-run | VALIDATED |

---

## 3. Validation Levels Achieved

| Subsystem | Level | Description |
|-----------|-------|-------------|
| Data ingestion (OM archive) | 4 | REAL provider, manifest checksums, SHA-256 verified |
| Data ingestion (NASA POWER) | 4 | REAL grid provider, 1981-2023 |
| Twin synchronization | 3 | Historical backtest; sync equality verified |
| Tmax forecasting | — | ENVIRONMENT_BLOCKED (torch broken) |
| Tmin forecasting | — | ENVIRONMENT_BLOCKED |
| Rainfall forecasting | — | ENVIRONMENT_BLOCKED |
| PET (Hargreaves-Samani) | 1 | Reference equation validated; no external ET data |
| AET (soil-limited) | 2 | Physical consistency verified; no external AET data |
| Soil-water storage | 2 | Mass balance exact, bounds enforced; no observed soil moisture |
| Runoff (SCS-CN) | 1 | Reference equation validated; no gauge/reanalysis data |
| SPEI | 1 | L-moments verified; no independent SPEI dataset |
| Heat hazard | 3 | Full-record backtest; works as designed |
| Heavy-rain hazard | 3 | Full-record backtest; works as designed |
| Dryness hazard | 3 | Full-record backtest; works as designed |
| Coupled simulator | 2 | Multi-year replay, physical consistency; no empirical validation |
| Counterfactual scenarios | 2 | Deterministic perturbations; no validation anchor |

---

## 4. Dataset Lineage

| Dataset | Provider | Variables | Period | Records | Purpose | Independent? |
|---------|----------|-----------|--------|---------|---------|-------------|
| data/real/training.csv | Open-Meteo Archive API | Tmax, Tmin, Rainfall | 2021-07-30 -> 2025-01-27 | 1,278 | ML training | — (training set) |
| data/real/validation.csv | Open-Meteo Archive API | Tmax, Tmin, Rainfall | 2025-01-28 -> 2025-10-28 | 274 | Early stopping, checkpoint selection | Yes (from training) |
| data/real/testing.csv | Open-Meteo Archive API | Tmax, Tmin, Rainfall | 2025-10-29 -> 2026-07-30 | 275 | Model evaluation + operational input | Partial (dual-use, no leakage) |
| data/raw/maxtemp.parquet | NASA POWER | MaxTemp | 1981 -> 2023 | 753,840 | Grid forcing + legacy training | — |
| data/raw/mintemp.parquet | NASA POWER | MinTemp | 1981 -> 2023 | 753,840 | Grid forcing | — |
| data/raw/rainfall.parquet | NASA POWER | Rainfall | 1981 -> 2023 | 753,840 | Grid forcing + hazard backtest | — |
| data/real/dataset_manifest.json | Internal | SHA-256 checksums | — | 3 checksums | Integrity verification | N/A |

**Leakage audit result: PASS.** Chronological splits are clean (no date overlap). Scalers fitted on training only. Rolling features are backward-looking. Hyperparameter tuning uses training-only cross-validation. Hazard thresholds are hardcoded, not data-derived. One concern: `testing.csv` serves dual role as model evaluation and operational input — namespace confusion but not data leakage.

**Cross-provider disagreement** (Open-Meteo vs NASA POWER, 885 overlapping days, 2021-2023):

| Variable | Bias (OM - NP) | MAE | RMSE | Correlation |
|----------|---------------|-----|------|-------------|
| Tmax | -2.01 degC | 2.19 degC | 2.68 degC | r=0.858 |
| Tmin | -1.11 degC | 1.30 degC | 1.55 degC | r=0.923 |
| Rainfall | -0.28 mm | 3.01 mm | 10.60 mm | r=0.325 |

Open-Meteo is systematically cooler by ~2degC (Tmax) compared to NASA POWER. The two providers barely agree on daily rainfall (r=0.325). The Twin's "REAL" temperature depends on which provider is chosen — this uncertainty exceeds the forecast model's claimed RMSE.

---

## 5. Forecast Validation

### Status: ENVIRONMENT_BLOCKED

All 6 registered model checkpoints require PyTorch inference which is broken on this machine (c10.dll, WinError 1114). Cannot reproduce Phase 3 metrics. Stored ForecastStore contains 2 single-day entries — insufficient for statistical validation.

### Persistence Baseline (275 test samples)

| Target | MAE | RMSE | Bias | R^2 | Pearson r |
|--------|-----|------|------|-----|-----------|
| Tmax | 0.93degC | 1.21degC | -0.00 | 0.851 | 0.926 |
| Tmin | 0.68degC | 0.94degC | -0.02 | 0.872 | 0.936 |
| Rainfall | 1.32 mm | 3.47 mm | -0.01 | -0.524 | 0.238 |

### Climatology Baseline

| Target | MAE | RMSE | Bias | R^2 | Skill vs Persistence |
|--------|-----|------|------|-----|---------------------|
| Tmax | 1.22degC | 1.59degC | -0.13 | 0.742 | -0.316 (worse) |
| Tmin | 1.22degC | 1.54degC | -0.51 | 0.658 | -0.636 (worse) |
| Rainfall | 1.97 mm | 3.09 mm | +1.29 | -0.209 | +0.109 (better) |

### Seasonal Breakdown (persistence RMSE)

| Target | Monsoon (Jun-Sep) | Dry (Dec-May) |
|--------|-------------------|---------------|
| Tmax | 1.38degC | 1.17degC |
| Tmin | 0.51degC | 1.00degC |
| Rainfall | 4.16 mm | 3.43 mm |

### Forecast Extremes

Rainfall wet-day detection (persistence): P=0.803, R=0.797, F1=0.800. Top 10% rainfall (>=9.2mm/day): RMSE=8.11 mm. Top 5%: RMSE=10.74 mm. Extreme rainfall forecasting is poor even for the baseline.

**Key finding**: Persistence (yesterday=today) is a formidable baseline for temperature — R^2 > 0.85. Any ML model claiming to improve on this must demonstrate skill relative to persistence, not just report absolute RMSE. Climatology is slightly better than persistence for rainfall but much worse for temperature.

---

## 6. Twin Synchronization Validation

The four-layer authenticity guard is correctly implemented at `twin_sync_service.py:74`, `:83`, `versioned_state_store.py:103`, `twin_service.py:113`. Delta guard at `bhai_state_manager.py:29-39`.

### Provenance Gaps Found

| Issue | Location | Severity |
|-------|----------|----------|
| `twin_version = entity_id` (not actual version number) | `twin_adapter.py:73` | Medium |
| `min_temp = max_temp = temperature_2m` (no separate min_temp) | `twin_adapter.py:60-61` | Low |
| Optional fields fall back to prior state when None (lossy) | `twin_sync_service.py:165-170` | Low |
| No periodic contamination sweep of stored states | versioned_state_store | Low |

Version history works correctly: parquet files with monotonic version numbers, parent lineage, version_index.parquet.

---

## 7. PET Validation

**Status: REFERENCE_VERIFIED, NOT EMPIRICALLY VALIDATED**

FAO-56 Example 20 reproduced: Ra=40.55 MJ/m2/day, ET0=5.03 mm/day (abs error 0.01). Correct implementation. No independent ET/PET reference data available in project. Hargreaves-Samani is the FAO-recommended temperature-only method — chosen because humidity/wind/radiation are unavailable. The krs=0.0023 coefficient is a literature value, not site-calibrated. Recommend acquiring ERA5-Land or GLEAM ET data for cross-reference.

---

## 8. Soil-Water Storage Validation

**Status: PHYSICALLY PLAUSIBLE, NOT EMPIRICALLY VALIDATED**

Mass balance exact (residual=0.0mm), bounds enforced, seasonal cycle plausible. No in-situ soil moisture or satellite data (SMAP, ESA CCI) comparison exists. Parameters are literature values, not site-measured. `soil_moisture_m3m3 = storage/capacity` is a relative proxy.

Parameter sensitivity: capacity shifts mean storage linearly. Depletion fraction has zero effect in current wet Bengaluru scenario. CN is the dominant control.

---

## 9. Runoff Validation

**Status: REFERENCE_VERIFIED, NOT EMPIRICALLY VALIDATED**

SCS-CN reference case: Q=25.7mm (abs error 0.2). Correct implementation. No streamflow gauge, runoff reanalysis, or GLDAS/ERA5-Land comparison possible.

### CN Sensitivity (dominant uncertainty source, 2-year synthetic forcing)

| CN | Total Runoff | Max Single-Day Runoff |
|----|-------------|----------------------|
| 40 | 0.0 mm | 0.0 mm |
| 50 | 47 mm | 0.6 mm |
| 60 | 227 mm | 2.7 mm |
| 70 (default) | 618 mm | 6.4 mm |
| 80 | 1,315 mm | 11.7 mm |
| 90 | 2,624 mm | 19.2 mm |
| 95 | 3,834 mm | 24.1 mm |

CN dominates all other parameter effects. A shift from CN=70 to CN=80 doubles runoff. At CN=95, runoff steals water from AET. Without empirical calibration, CN=70 is a plausible but unverified assumption.

---

## 10. SPEI Validation

**Status: REFERENCE_VERIFIED, PARTIALLY VALIDATED**

L-moment implementation verified independently. Monsoon months (Jun-Sep) have mean SPEI +1.11, dry months -0.59. Overall mean=-0.014, std=1.061 (close to N(0,1)). Correct implementation confirmed.

Limitations: no independent SPEI dataset compared; scale-3 only tested; fallback to standardized anomaly for short windows; monthly_d_from_daily hardcodes lat=12.97.

---

## 11. Hazard Intelligence Backtest

### Full Bengaluru OM Record (1827 days, 2021-07-30 to 2026-07-30)

**HEAT** — 74 events (Tmax > 35degC), all LOW (score < 20). Max: 18.0 at 39.5degC (2024-05-01). Detection at >35degC: 74/77 (96.1%). The 35degC threshold and 4x scaling means Bengaluru never reaches MODERATE heat — this may be correct for the city's climate.

**HEAVY_RAIN** — No SEVERE events in OM record. Max: 69.6mm (2021-11-18), score 34.8 (MODERATE). The 100mm SEVERE threshold is never triggered by OM Bengaluru. NASA POWER grid has 266.32mm at cell (12.5N, 78.0E) ~60km away.

**DRYNESS** — 21 dry spells of 10+ consecutive days. Longest: 93 days (Jan-Apr 2024). Corresponds correctly to Bengaluru dry season.

### Hazard Metrics Summary

| Hazard | Records | Threshold | Events | Max Severity |
|--------|---------|-----------|--------|-------------|
| HEAT | 1827 | Tmax>35degC | 74 (4.1%) | LOW (18.0) |
| HEAVY_RAIN | 1827 | Rain>100mm | 0 (0%) | NONE |
| DRYNESS | 1827 | 10+ dry days | 21 spells | — |

### Code Bugs Confirmed

| Bug | Location | Impact |
|-----|----------|--------|
| Confidence count always 1 | `hazard_evaluator.py:362` | Broken confidence calculation |
| Only highest-scoring hazard returned | `hazard_evaluator.py:327` | Concurrent extremes lost |
| risk_config.yaml loaded but never applied | `hazard_evaluator.py:72` | Dead config — hardcoded defaults rule |
| SEVERE threshold: code>60 vs config>80 | quality_gate vs config | Config mismatch (code wins) |
| "Agriculturally calibrated" is false | `heat_risk.py` — no crop factors | Mislabeled claim |

---

## 12. Coupled Simulation Multi-Year Validation

Run over full 1827-day Bengaluru OM record with 90-day spinup. Mass balance exact (0.0mm). Storage always in [0,150]mm. Tracks monsoon-dry seasonal cycle correctly. Deterministic. No REAL-store contamination. Without independent validation data, remains a reference-verified physical model — not an empirically validated twin.

---

## 13. Cross-Provider Validation

The two REAL providers disagree significantly on critical variables. The 2degC Tmax bias means the Twin's "true" temperature depends on provider choice. The r=0.325 rainfall correlation means providers disagree more than agree on daily precipitation.

---

## 14. Parameter Sensitivity

| Parameter | Effect | Dominance |
|-----------|--------|-----------|
| `cn_ii` | Controls runoff 0-3834mm; CN=70->618, CN=90->2624 | CRITICAL |
| `capacity_mm` | Shifts mean storage linearly; no effect on AET/drainage | MODERATE |
| `depletion_fraction` | Zero effect (storage rarely depletes) | LOW |
| `initial_storage_mm` | Fully converges within 90-day spinup | NEGLIGIBLE |
| `krs` | Linear PET scaling; affects AET when storage-limiting | MODERATE |

Initial condition convergence: all five ICs (0, 37.5, 75, 112.5, 150mm) converge to 144.9mm by day 90. Spinup is adequate.

---

## 15. Calibration

No calibration performed — no independent measurements exist for CN, storage capacity, or ET. Calibrating without independent validation data is curve-fitting, not science. All parameters remain LITERATURE DEFAULTS, classified as UNCALIBRATED.

---

## 16. Failure Analysis

### Worst Cases

| Subsystem | Failure | Detail |
|-----------|---------|--------|
| Forecast | MODEL_UNAVAILABLE | Torch c10.dll blocks all models; degrades to 503 |
| PET | No validation possible | Zero external ET data |
| Runoff | Uncalibrated CN | CN=70 is a guess; real value could be 50-90 |
| Cross-provider | 2.68degC Tmax RMSE | Providers disagree on basic temperature |
| Hazard confidence | count=1 always | `hazard_evaluator.py:362` structurally broken |
| Hazard severity | Config/code mismatch | SEVERE at >60 (code) vs >80 (config) |
| Twin version | Lost version | `twin_adapter.py:73` stores entity_id not version |

---

## 17. Scientific Status Table

| Component | Status | Level | Main Evidence | Main Limitation |
|-----------|--------|-------|---------------|-----------------|
| Data ingestion (OM) | VALIDATED | 4 | SHA-256 manifest, 1827 records | Provider disagreement with NASA POWER |
| Data ingestion (NASA POWER) | VALIDATED | 4 | Parquet 753,840 rows | Grid cell != point observation |
| Twin synchronization | PARTIALLY_VALIDATED | 3 | 4-layer guard, chronological versions | twin_version lost, optional fields lossy |
| Tmax forecasting | ENVIRONMENT_BLOCKED | — | Cannot load models | Persistence R^2=0.851 |
| Tmin forecasting | ENVIRONMENT_BLOCKED | — | Cannot load models | Persistence R^2=0.872 |
| Rainfall forecasting | ENVIRONMENT_BLOCKED | — | Cannot load models | All models near-zero/negative R^2 |
| PET | REFERENCE_VERIFIED | 1 | FAO-56 Ex.20: 5.03 mm/day | No external ET data |
| AET | PHYSICALLY_PLAUSIBLE | 2 | Soil-limited, non-negative, <=PET | No external AET data |
| Soil-water storage | PHYSICALLY_PLAUSIBLE | 2 | Mass balance exact, bounds enforced | No soil moisture observations |
| Runoff | REFERENCE_VERIFIED | 1 | Published example: 25.7mm | CN uncalibrated; no gauge data |
| SPEI | PARTIALLY_VALIDATED | 1 | L-moments verified; pattern correct | No independent SPEI comparison |
| Heat hazard | PARTIALLY_VALIDATED | 3 | 74 events backtested, 96% detection | All LOW; no heatwave tracking |
| Heavy-rain hazard | PARTIALLY_VALIDATED | 3 | Backtested; OM never triggers SEVERE | NASA POWER has extremes OM lacks |
| Dryness hazard | PARTIALLY_VALIDATED | 3 | 21 dry spells, 93-day longest | Single-day 0mm is normal |
| Counterfactual scenarios | PHYSICALLY_PLAUSIBLE | 2 | Deterministic perturbations | No validation anchor |
| Coupled simulator | PHYSICALLY_PLAUSIBLE | 2 | Multi-year replay, consistent | No empirical validation of any output |

---

## 18. What The Project Can Scientifically Claim

The Climate Digital Twin is a real-data climate intelligence prototype with verified observation ingestion, physical water-balance simulation (Hargreaves-Samani ET + SCS-CN runoff + bucket storage + SPEI drought index), and basic hazard threshold scoring. Data authenticity is enforced through SHA-256 manifests, provenance chains, and strict REAL-only gates. The system correctly tracks Bengaluru's monsoon-driven seasonal cycle but its forecasts are blocked by environment issues, its land-surface outputs are uncalibrated, and its hazard scores are deterministic threshold mappings, not calibrated event probabilities.

---

## 19. What The Project CANNOT Claim

The system is NOT:
- A full atmospheric climate model or numerical weather prediction system
- A validated flood prediction system (no river discharge, terrain, or drainage data)
- A validated drought impact prediction system (no crop model, no Palmer Index, no impact data)
- An India-wide calibrated hydrological model (single-location, uncalibrated parameters)
- A physics-complete Earth-system Digital Twin (missing atmosphere, groundwater, vegetation dynamics)
- A heatwave prediction system (no multi-day consecutive high-temperature tracking)
- A storm prediction system (no radar, no nowcasting, no pressure/wind dynamics)
- An AGI/LLM weather expert (copilot responses are LLM-generated text, not scientific model output)

---

## 20. Production Regression

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| Phase 5 scenario tests | 24 | 0 | 0 |
| Phase 5 regressions | 8 | 0 | 0 |
| Phase 6 integrity | 12 | 0 | 0 |
| Phase 7 simulation core | 27 | 0 | 0 |
| Phase 7 replay | 11 | 0 | 0 |
| Dashboard | 209 | 0 | 1 |
| Copilot | passed | 0 | 0 |
| **Total verified** | **291+** | **0** | **1** |

All Phase 1-7 targeted tests pass. No production code modified during Phase 8.

---

## 21. Final Scientific Scorecard

| Category | Score /100 | Basis |
|----------|-----------|-------|
| Software engineering maturity | 85 | Clean architecture, deterministic engine, comprehensive tests, provenance tracking |
| Data authenticity | 90 | SHA-256 manifests, strict REAL gates, no SIMULATED contamination; cross-provider disagreement unresolved |
| Forecast scientific validity | 15 | Models inaccessible; persistence is strong baseline; all models have near-zero rainfall R^2 |
| Twin fidelity | 75 | Core fields exact; minor provenance losses; no periodic contamination sweeps |
| Land-surface simulation validity | 40 | Equations reference-verified; no empirical validation; dominant CN parameter uncalibrated |
| Hazard validation | 35 | Backtested correctly but deterministic rules; broken confidence calculation; single-hazard output |
| Provenance/auditability | 85 | Full chain traceable; some gaps (config not applied, twin_version lost) |
| Production readiness | 60 | Tests pass; torch blocks inference; docker down; single-location only |
| **Overall scientific confidence** | **55** | A climate intelligence prototype with strong engineering — not a validated prediction system |

---

## 22. Remaining Scientific Gaps

| Gap | Severity | Action |
|-----|----------|--------|
| No forecast model inference possible | CRITICAL | Fix PyTorch environment (WSL2, Linux, or fixed DLLs) |
| No runoff/gauge validation data | HIGH | Acquire CWC streamflow data or ERA5-Land/GLDAS runoff reanalysis |
| No soil moisture validation | HIGH | Acquire SMAP or ESA CCI Soil Moisture for Bengaluru cell |
| No ET validation data | HIGH | Acquire ERA5-Land or GLEAM ET for comparison |
| Cross-provider 2degC Tmax disagreement | HIGH | Investigate cause; consider meteorological station data as tiebreaker |
| CN is uncalibrated | MEDIUM | Land-cover classification + soil survey for Bengaluru |
| Broken hazard confidence calculation | MEDIUM | Fix `hazard_evaluator.py:362` to use actual available-data count |
| Dead risk_config.yaml | MEDIUM | Wire config severity/jitter/freshness thresholds into quality gate |
| Single hazard per assessment | MEDIUM | Support concurrent multi-hazard output |
| Single-location only | MEDIUM | Extend validation to 2-3 additional Karnataka grid cells |
| No seasonal forecast evaluation for models | LOW | Requires working model inference first |
| No drought SPEI external comparison | LOW | Compare against SPEI Global Drought Monitor for same period |
| Testing.csv dual use | LOW | Rename to operational.csv or split into separate files |

---

## 23. Recommended Next Work

Phase 8 evidence dictates the priority order:

1. **Fix PyTorch environment** (CRITICAL) — without this, forecast validation cannot proceed and the best model claim remains untestable
2. **Acquire external validation data** (HIGH) — ERA5-Land ET + runoff + soil moisture for Bengaluru cell; this enables empirical validation of all Phase 7 outputs
3. **Fix hazard evaluator bugs** (MEDIUM) — broken confidence calculation, dead config wiring, single-hazard limitation
4. **Site-specific calibration** (MEDIUM) — once validation data exists, calibrate CN and storage capacity against observations
5. **Multi-location validation** (MEDIUM) — extend to 2-3 NASA POWER grid cells in Karnataka
6. **Cross-provider resolution** — determine which REAL provider is authoritative or document the uncertainty formally

The next phase should be driven by observed weaknesses, not by adding features. Phase 8's primary finding is that the system needs more validation data, not more code.

---

## 24. DoD Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | All major scientific claims registered | PASS |
| 2 | Dataset lineage documented | PASS |
| 3 | Leakage audit passes | PASS |
| 4 | Forecast metrics reproduced independently | PARTIAL — environment-blocked; baselines computed |
| 5 | Forecast baselines evaluated | PASS |
| 6 | Forecast skill scores calculated | PASS (baselines) |
| 7 | Seasonal forecast performance measured | PASS (persistence) |
| 8 | Extreme-event forecast performance measured | PASS (persistence) |
| 9 | Twin synchronization numerically validated | PASS |
| 10 | Twin provenance/version integrity validated | PASS (gaps documented) |
| 11 | PET receives independent validation | INSUFFICIENT_DATA (no external data) |
| 12 | Soil-water state receives independent validation | INSUFFICIENT_DATA |
| 13 | Runoff receives independent validation | INSUFFICIENT_DATA |
| 14 | SPEI independently cross-checked | PASS (manual L-moment verification) |
| 15 | Heavy-rain hazard backtested | PASS |
| 16 | Heat hazard backtested | PASS |
| 17 | Dryness hazard compared with evidence | PASS |
| 18 | Coupled simulator receives multi-year validation | PASS (internal consistency) |
| 19 | Cross-provider disagreement quantified | PASS |
| 20 | Parameter sensitivity quantified | PASS |
| 21 | Initial-condition sensitivity quantified | PASS |
| 22 | Spin-up adequacy tested | PASS |
| 23 | Calibration/validation periods separated | PASS (no calibration performed) |
| 24 | Candidate calibrated parameters isolated | N/A (no calibration) |
| 25 | Baselines included | PASS |
| 26 | Negative skill reported | PASS |
| 27 | Failure cases documented | PASS |
| 28 | Validation uncertainty reported | PASS (parameter sensitivity) |
| 29 | No fake uncertainty introduced | PASS |
| 30 | No synthetic ground truth used | PASS |
| 31 | No self-validation occurs | PASS |
| 32 | External datasets have provenance | N/A (none acquired) |
| 33 | Validation artifacts reproducible | PASS (scripts in scripts/phase8_*) |
| 34 | Production stores remain unchanged | PASS |
| 35 | Phase 1-7 functionality remains regression-free | PASS |
| 36 | Each component receives scientific status | PASS |
| 37 | Each component receives validation level | PASS |
| 38 | Unsupported claims downgraded | PASS (C15 FAILED_VALIDATION) |
| 39 | PHASE8_FINAL_REPORT.md produced | PASS |
| 40 | Final project scientific classification evidence-based | PASS |

---

*Generated: 2026-08-01 | Phase 8 Scientific Validation — Read-Only Audit*
