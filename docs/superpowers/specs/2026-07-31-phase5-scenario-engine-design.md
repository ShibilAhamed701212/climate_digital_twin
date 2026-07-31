# Phase 5 Implementation Specification — Real Counterfactual / What-If Scenario Engine

**Date:** 2026-07-31
**Project:** Climate Digital Twin — ISRO BAH 2026 Challenge 5
**Status:** READY FOR REVIEW
**Supersedes:** the fake/hardcoded internals of `climatedt/scenario/service.py` and the
demo `simulator` scenario stack as the PRODUCTION scenario path.

---

## 0. Classification

This feature is a **COUNTERFACTUAL / WHAT-IF DIGITAL TWIN SIMULATION**.

It answers one question:

> "If we hypothetically alter these Twin variables at a given instant, what would the
> existing Phase 4 hazard intelligence system report?"

It is **NOT** a climate prediction, **NOT** a physics-based climate simulator,
**NOT** a causal model, and **NOT** a probabilistic simulator. It applies deterministic
arithmetic perturbations to a snapshot of the authoritative REAL Twin state and re-runs
the same Phase 4 hazard formulas. Every scenario-derived artifact is labelled
`authenticity = SCENARIO`. Scenario outputs must **never** be presented as observed,
forecast, or live operational state.

---

## 1. Mandatory Isolation Correction (non-negotiable)

The legacy demo path currently **mutates authoritative REAL Twin state**:

```
simulator/services/scenario_service.py
  └─ self.twin.apply_scenario(entity, scenario_id)
       └─ simulator/services/twin_service.py::apply_scenario  (line ~103)
            └─ writes scenario-modified state into the REAL Twin repository
```

**Rule:** Demo functionality may remain, but no demo/experimental scenario path may
mutate authoritative REAL Twin state. Fix order (defense in depth — do BOTH):

1. **Fix the caller** — legacy demo output stays in-memory or in a DEMO-specific
   store; it never writes to the Twin repository.
2. **Protect the boundary** — `TwinService.apply_scenario` (and the repository write
   layer it uses) must **hard-reject** any state whose `authenticity` is not `REAL`.

**Final invariant: `ANY SCENARIO PATH → AUTHORITATIVE REAL TWIN WRITE = IMPOSSIBLE`.**

---

## 2. Architecture

```
Dashboard (page 04 — Scenario Simulator)
   │  api_client → gateway (NOT :8002)
   ▼
FastAPI gateway  (backend/api/main.py)
   ▼
backend/api/routes/scenario.py   ── REAL endpoints ──────────────┐
   │  /scenario/create  /scenario/run  /scenario/{id}            │
   │  /scenario/list    /scenario/history  /scenario/compare     │
   ▼                                                            │
climatedt/scenario/service.py                                  │
   │  ScenarioService                                           │
   ├── TwinStateManager.get_current_state(location_id)  ── REAL Twin (authoritative)
   │        │  authenticity must be REAL
   │        ▼
   │  immutable baseline snapshot (TwinState, authenticity=REAL, timestamp=T)
   │        ▼
   ├── ScenarioEngine.apply(baseline, interventions) → TwinState(authenticity=SCENARIO)
   │        │  deterministic ops: ADD SUBTRACT MULTIPLY SET PERCENT_CHANGE
   │        ▼
   ├── HazardEvaluator.assess_observed(baseline_inputs)   → baseline hazard (OBSERVED)
   ├── HazardEvaluator.assess_scenario(scenario_inputs)   → scenario hazard (SCENARIO)
   │        │  both NON-persisting — no HazardStore, no AlertStore writes
   │        ▼
   └── ScenarioStore.save_result(...)   → data/scenarios/ (definitions, results, comparisons)
        NEVER ObservationStore / ForecastStore / Twin repository / HazardStore / AlertStore

Legacy demo stack (simulator/*, :8002) — KEPT, clearly marked DEMO/EXPERIMENTAL,
   isolated: MonteCarloEngine, PerturbationEngine, EnsembleSimulator, ScenarioGenerator,
   /scenario/monte-carlo-sim, /scenario/compare-scenarios, /scenario/ensemble,
   /scenario/scenario-generator, /scenario/monte-carlo, /scenario/generate/{template}.
```

### Data-flow invariants

- **Every** scenario artifact (definition, scenario state, result, comparison) carries
  `authenticity = SCENARIO`. The baseline may be `REAL`, but scenario output **never**
  inherits `REAL`.
- `HazardEvaluator.assess_scenario()` reuses the exact Phase 4 formulas
  (`_compute_assessment`) with `AssessmentType.SCENARIO`. It does **not** persist, does
  **not** create alerts, does **not** become the current operational hazard, and is never
  returned by observed/forecast endpoints.
- Single-timestamp counterfactual. `simulation_horizon`/`duration_days` is **metadata
  only** (a label on the definition), never a time axis.
- `:8002` remains the DEMO/EXPERIMENTAL microservice. It is not a competing production
  path. The dashboard calls the **gateway**.

---

## 3. Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `climatedt/scenario/models.py` | Canonical `ScenarioDefinition`, `ScenarioIntervention`, `ScenarioResult`, `ScenarioComparison`, units & bounds tables, `SCENARIO_AUTHENTICITY`, content-hash identity |
| 2 | `climatedt/scenario/engine.py` | `ScenarioEngine` — deterministic perturbation application, physical-bounds validation, no NumPy/`random` in the core path |
| 3 | `climatedt/scenario/store.py` | `ScenarioStore` — JSONL persistence under `data/scenarios/` (`definitions.jsonl`, `results.jsonl`), restart recovery, content-hash idempotency |

## 4. Files to Rewrite

| # | File | Change |
|---|------|--------|
| 4 | `climatedt/scenario/service.py` | Replace fake internals: no hardcoded `{max_temp:30,min_temp:20,rainfall:50}`, no fallback fake weather, no `scenario_id`-as-`location_id` bug, no empty MC/compare stubs. Real flow: REAL twin baseline → engine → scenario hazard → comparison → store |
| 5 | `risk/evaluation/hazard_evaluator.py` | Add `assess_scenario(twin_inputs, location_id)` → `HazardAssessment` with `AssessmentType.SCENARIO`, non-persisting, no alert creation |
| 6 | `simulator/services/scenario_service.py` | Stop calling `TwinService.apply_scenario`; demo output stays in-memory/DEMO-scoped |
| 7 | `simulator/services/twin_service.py` | Guard `apply_scenario`: reject any state with `authenticity != "REAL"` |
| 8 | `backend/api/routes/scenario.py` | Wire `/scenario/create`, `/run`, `/{id}`, `/compare` to the real service; add `/scenario/list` + `/scenario/history`; mark demo endpoints with `mode="DEMO"` / `authenticity="SYNTHETIC"` in responses |
| 9 | `dashboard/services/api_client.py` | Scenario calls hit the gateway, not `SCENARIO_ENGINE_URL` (:8002) |
| 10 | `dashboard/page_views/04_scenario_simulator.py` | Render WHAT-IF/SCENARIO badge, baseline vs scenario values, deltas, baseline & scenario hazards; never present hypothetical as live |

## 5. Files to Create (tests)

| # | File | Purpose |
|---|------|---------|
| 11 | `tests/unit/test_phase5_scenario.py` | Validation, determinism, idempotency, isolation, authenticity, restart recovery |
| 12 | `tests/unit/test_phase5_regressions.py` | The 5 regression tests (below) |

---

## 6. Data Model

### `ScenarioIntervention`

```
variable: str      # one of SUPPORTED_VARIABLES
operation: str     # ADD | SUBTRACT | MULTIPLY | SET | PERCENT_CHANGE
value: float       # for ADD/SUBTRACT: absolute delta in `unit`;
                   # for MULTIPLY: multiplier; SET: target value in `unit`;
                   # PERCENT_CHANGE: percentage (e.g. 50 → +50%, -20 → -20%)
unit: str          # must match the variable's canonical unit
```

Supported variables & physical bounds (post-application value must be within bounds or the
intervention is **rejected**, never silently clamped):

| variable | unit | bounds |
|----------|------|--------|
| `temperature_2m` | `°C` | unbounded (reject NaN/Inf) |
| `precipitation_mm` | `mm` | `>= 0` |
| `humidity_pct` | `%` | `[0, 100]` |
| `pressure_hpa` | `hPa` | `[850, 1080]` |
| `wind_speed_10m` | `m/s` | `>= 0` |
| `wind_direction_10m` | `deg` | `[0, 360)` |
| `cloud_cover_pct` | `%` | `[0, 100]` |
| `soil_moisture` | `m³/m³` | `>= 0` |
| `solar_radiation` | `W/m²` | `>= 0` |

**Validation (reject with a clear `ValueError`):**

- unknown variable, unknown operation;
- `value` is NaN or Inf;
- post-application value falls outside the physical bounds;
- `PERCENT_CHANGE` on a **zero baseline value**:
  `"PERCENT_CHANGE has no effect on a zero baseline; use ADD or SET for an absolute hypothetical rainfall scenario."`
- `MULTIPLY` by a negative factor when the variable is non-negative-bounded;
- baseline missing (no REAL twin state for `location_id`) → raise, **never** substitute
  hardcoded weather.

### Identity & idempotency

`result_id` is the SHA-256 of a canonical JSON payload:

```
location_id
baseline_twin_version        (entity_id of the REAL twin)
baseline_timestamp           (ISO 8601 UTC, from the baseline TwinState)
interventions                (ordered list of normalized {variable, operation, value, unit})
method                       ("counterfactual")
method_version               ("1.0.0")
config_version               ("2026-07-31")
```

Not just `scenario_id` — the same definition re-run against a newer baseline twin is a
**new** result. Identical inputs → identical `result_id` (idempotency) and identical
values (determinism).

### `ScenarioResult`

```
result_id            content hash (above)
scenario_id
definition           snapshot of the ScenarioDefinition used
location_id
baseline_twin_version
baseline_timestamp
baseline_state       dict of variable → baseline value (REAL)
scenario_state       dict of variable → hypothetical value (SCENARIO)
deltas               dict of variable → (scenario - baseline)  (absolute; % for percent ops)
baseline_hazard      HazardAssessment snapshot (OBSERVED, non-persisted)
scenario_hazard      HazardAssessment snapshot (SCENARIO, non-persisted)
hazard_deltas        dict of hazard_type → scenario_score - baseline_score
authenticity         "SCENARIO"
mode                 "REAL"
execution_time_ms
created_at
```

### `ScenarioComparison`

```
comparison_id        content hash of the two result_ids
baseline_result_id
scenario_result_id
variable_deltas
hazard_deltas        dict hazard_type → {baseline_score, scenario_score, delta}
summary              human-readable sentence
```

---

## 7. Engine Semantics

`ScenarioEngine.apply(baseline: TwinState, interventions) -> TwinState`:

1. `values[v] = getattr(baseline, v)` for each supported variable.
2. Apply each intervention in order: `ADD: x+v`, `SUBTRACT: x-v`, `MULTIPLY: x*v`,
   `SET: v`, `PERCENT_CHANGE: x*(1+v/100)`.
3. Round every value to 2 decimals.
4. Validate physical bounds — reject on violation.
5. Return `dataclasses.replace(baseline, <perturbed fields>,
   authenticity="SCENARIO", data_source="scenario", quality_flag="simulated",
   metadata={**baseline.metadata, "scenario_id":..., "baseline_authenticity":"REAL"})`.

No `random`, no NumPy in the core path. Deterministic.

---

## 8. Hazard Integration

`HazardEvaluator.assess_scenario(twin_inputs, location_id)`:

- Calls `_compute_assessment(assessment_type=AssessmentType.SCENARIO, ...)` with
  `quality=DataQuality.GOOD` and `freshness=check_freshness(baseline.timestamp)`.
- Does **not** write to `HazardStore` or `AlertStore`, does **not** evaluate the
  `AlertPolicy`.
- Reuses `extract_twin_inputs` (so provenance carries `authenticity=SCENARIO`).

The **baseline** hazard uses the existing `assess_observed` (also non-persisting) with
`AssessmentType.OBSERVED`; delta = scenario − baseline per hazard type.

---

## 9. API Contract (unchanged routes keep behavior; existing tests must stay green)

| Route | Status | Behavior |
|-------|--------|----------|
| `POST /scenario/create` | **REAL** | build canonical definition from `CreateScenarioRequest` (deltas mapped to interventions; `interventions` field also accepted), save, return `scenario_id` (201) |
| `POST /scenario/run` | **REAL** | load → run against REAL twin → `RunScenarioResponse` extended with `authenticity`, `mode`, baseline/scenario values, hazards; 404 if unknown |
| `GET /scenario/{scenario_id}` | **REAL** | `ScenarioDetailResponse` extended with `interventions`, `authenticity`, `location_id` |
| `POST /scenario/compare` | **REAL** | run both scenarios, produce `ScenarioComparison`s |
| `GET /scenario/templates` | unchanged | must keep exactly 9 templates (test-pinned) |
| `GET /scenario/list` | **NEW** | list saved scenario definitions (id, name, type, location_id, created_at) |
| `GET /scenario/history` | **NEW** | list saved scenario results (result_id, scenario_id, location_id, created_at) |
| `POST /scenario/generate/{template}` | demo | unchanged (mocked in tests); responses tagged demo |
| `POST /scenario/monte-carlo` | demo | unchanged; tagged demo |
| `POST /scenario/monte-carlo-sim` | demo | unchanged; tagged demo |
| `POST /scenario/compare-scenarios` | demo | unchanged; tagged demo |
| `POST /scenario/ensemble` | demo | unchanged; tagged demo |
| `POST /scenario/scenario-generator` | demo | unchanged; tagged demo |

---

## 10. E2E Scenarios (REAL Bengaluru twin `KA-BLR-001`)

Baseline (from `~/.climatedt/data/twin_state/KA-BLR-001/v000001.parquet`, run
`20260730T143413Z_07bfa5`): 22.1°C, 0.0 mm, 88 % RH, 907.5 hPa, 16.6 m/s, 100 % cloud.

| # | Name | Interventions | Expected |
|---|------|---------------|----------|
| A | Bengaluru +3°C | `temperature_2m ADD 3` | 25.1°C; report baseline/scenario values + deltas + baseline HEAT assessment + scenario HEAT assessment + hazard delta |
| B | Bengaluru 50mm rain | `precipitation_mm SET 50` (NOT +50% — baseline is 0 mm) | 50.0 mm; classified `hypothetical absolute rainfall intervention`; flood + dryness deltas |
| C | Bengaluru +3°C +5% RH | `temperature_2m ADD 3` + `humidity_pct ADD 5` | 25.1°C / 93 % RH |

Historical extreme (single-timestamp counterfactual on a verified stored record):
- 2022-08-18, rainfall **~266.32 mm** — **VERIFY the value from stored data first**,
  then `precipitation_mm PERCENT_CHANGE 50` → ~399.48 mm **derived from the verified
  value** (not hardcoded).

---

## 11. Mandatory Tests & Invariants

Isolation (must all be NO):
- `REAL_TWIN_MUTATED = NO`
- `OBSERVATION_STORE_CONTAMINATED = NO`
- `FORECAST_STORE_CONTAMINATED = NO`
- `OPERATIONAL_HAZARD_CONTAMINATED = NO`
- `OPERATIONAL_ALERT_CREATED = NO`
- `LEGACY_DEMO_CAN_MUTATE_REAL_TWIN = NO`
- `SCENARIO_ARTIFACT_LABELLED_REAL = NO`
- `SCENARIO_RESTART_RECOVERY = PASS`
- Defense-in-depth: passing SCENARIO state to authoritative Twin persistence **must
  reject**.

5 regression tests:
1. `climatedt/scenario/service.py` must not contain hardcoded 30/20/50 baseline fallback.
2. `run_scenario` must not interpret `scenario_id` as `location_id`.
3. legacy `simulator/services/scenario_service.py` must not persist into authoritative
   REAL Twin storage.
4. SCENARIO hazard path must not invoke alert creation.
5. dashboard must not route scenario execution through :8002.

---

## 12. Production Crawl

Search `np.random`, `random`, `SYNTHETIC`, `synthetic`, `mock`, `fake`, `dummy`,
`fallback`, hardcoded baselines, `apply_scenario`, Twin/Observation/Forecast/AlertStore
writes. Classify each hit VERIFIED_PRODUCTION / DEMO-EXPERIMENTAL / TEST / LEGACY /
UNREACHABLE.

Required final results:
- Production random scenario transformations: **0**
- Production hardcoded baselines: **0**
- Production synthetic fallback: **0**
- Scenario → Twin write: **0**
- Scenario → ObservationStore write: **0**
- Scenario → ForecastStore write: **0**
- Scenario → operational AlertStore write: **0**
- Demo → authoritative REAL Twin write: **0**

---

## 13. Final Report

`PHASE5_FINAL_REPORT.md` at repo root must include:

- Baseline table + scenario A/B/C results + historical extreme result.
- Isolation test table (all NO / PASS as above).
- **`## Legacy/Demo Isolation`** section: Monte Carlo / Perturbation / Ensemble /
  ScenarioGenerator / :8002 classified DEMO / EXPERIMENTAL; legacy demo Twin mutation
  FIXED or NOT FIXED; final NO/NO/NO.
- Production crawl table with counts.
- Test summary (new Phase 5 tests + full-suite status).

---

## 14. Out of Scope (Phase 5)

- No deletion or upgrade of the demo Monte Carlo / ensemble stack.
- No probabilistic scenario engine in the production path.
- No multi-timestamp / time-series counterfactual.
- No Phase 6 work.
