# Production Data Migration Plan

**Date:** 2026-07-14
**Project:** Climate Digital Twin — ISRO BAH 2026 Challenge 5
**Status:** READY FOR IMPLEMENTATION

---

## 1. Current State Assessment

### Verified REAL (already in repo, no migration needed)

| Asset | Location | Details |
|-------|----------|---------|
| NASA POWER rainfall (1981-2011) | `data/raw/rainfall.parquet` | 753,840 rows, 0.25° grid |
| NASA POWER max temp (1981-2011) | `data/raw/maxtemp.parquet` | 753,840 rows, 1.0° grid |
| NASA POWER min temp (1981-2011) | `data/raw/mintemp.parquet` | 753,840 rows, 1.0° grid |
| Processed training data | `data/processed/training.csv` | 439,740 rows, 14 feature columns |
| Climate documents | `knowledge/documents/` | 5 real markdown files (IMD, ISRO, IPCC, govt) |

### Verified PARTIALLY REAL (uses real data but also synthetic)

| Component | Real | Synthetic | Location |
|-----------|------|-----------|----------|
| Pipeline | Downloads real NASA POWER | Falls back to `_generate_synthetic_*()` | `pipeline/download.py` |
| Data Loader | Reads processed data | Falls back to `_generate_synthetic_training_data()` | `models/data_loader.py` |
| Forecast Inference | Loads model weights | Falls back to `np.random.default_rng(42).uniform()` | `backend/services/forecast/inference.py` |

### Verified SYNTHETIC (entirely production — must be removed)

**Dashboard (4 files):**
- `dashboard/services/api_client.py` — `_synthetic_forecast()`, `_synthetic_current_state()`, `_synthetic_risk()`, `_synthetic_scenario_result()` — silent synthetic fallback on every API call
- `dashboard/page_views/08_knowledge_base.py` — 100% mock search results from `np.random`
- `dashboard/page_views/09_feedback.py` — 100% mock feedback data from `np.random.seed(42)`
- `dashboard/page_views/10_twin_state_bhai.py` — 100% mock twin state from `np.random.uniform/exponential/normal`

**Copilot (6 files):**
- `copilot/tools/forecast_tool.py` — `_synthetic_forecast()` — math.sin/cos fake
- `copilot/tools/twin_tool.py` — `_synthetic_twin_state()` — hardcoded fake
- `copilot/tools/risk_tool.py` — `_synthetic_risk()` — hardcoded fake
- `copilot/tools/scenario_tool.py` — `_synthetic_scenario()` — hardcoded fake
- `copilot/tools/report_tool.py` — `_synthetic_report()` — template text
- `copilot/tools/rag_tool.py` — `_synthetic_rag()` — hardcoded fake docs

**Knowledge (1 file):**
- `knowledge/embeddings/embedding_model.py` — `_get_dummy_embedding()` — hash-based fake embedding

**Risk (1 file):**
- `risk/explainability/shap_explainer.py` — `_estimate_shap_values()` — heuristic, not real SHAP

### Verified FAISS INDEX EMPTY
No `.faiss` or `.index` files exist anywhere in `knowledge/`. The 5 real markdown documents are not yet embedded.

---

## 2. Architecture

### 2.1 Four Runtime Data States

Every observation in the system must be classified into exactly one of four states:

| State | Meaning | Example | UI Badge |
|-------|---------|---------|----------|
| **LIVE** | Fresh observation from a live provider within TTL | Open-Meteo API response 2 minutes ago | 🟢 LIVE |
| **CACHED** | Previously downloaded real observation, still within cache window | NASA POWER data from last hour | 🟡 CACHED |
| **HISTORICAL** | Bundled archived dataset distributed with the repository | NASA POWER 1981-2011 from `data/raw/` | 🔵 HISTORICAL |
| **UNAVAILABLE** | No verified observation exists from any source | Provider down + no cache + no historical | ⚪ UNAVAILABLE |

HISTORICAL is distinct from CACHED:
- HISTORICAL data is bundled with the repo and never overwritten
- CACHED data was previously live but may be evicted
- The UI must label these differently with different badges

### 2.2 Data Flow

```
                     ┌─────────────────────┐
                     │   ProviderManager    │
                     │   (DataSourceManager)│
                     └──────────┬──────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   LIVE Provider         Cache Layer          Historical Store
   (NASA POWER,          (Parquet,            (data/raw/*.parquet)
    Open-Meteo,           TTL-based)           Bundled archive)
    IMD)
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   DataSourceManager   │
                    │                       │
                    │  Priority resolution  │
                    │  Failover             │
                    │  Circuit breaker      │
                    │  Retry                │
                    │  Freshness calc       │
                    │  Provenance metadata  │
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┼──────────────────────────┐
          │                     │                          │
          ▼                     ▼                          ▼
   ┌───────────┐        ┌─────────────┐          ┌────────────────┐
   │ Dashboard │        │   Copilot   │          │ Forecast/Risk/ │
   │           │        │   Tools     │          │ Scenario/Twin  │
   │ All pages │        │   (6 tools) │          │ Services       │
   │ via API   │        │   via API   │          │ via API        │
   └───────────┘        └─────────────┘          └────────────────┘
```

**Critical rule:** Every consumer must call `DataSourceManager`. Consumers must NEVER implement provider logic, fallback logic, or data generation themselves.

### 2.3 Data Provenance

Every observation returned by `DataSourceManager` includes:

```json
{
    "status": "LIVE" | "CACHED" | "HISTORICAL" | "UNAVAILABLE",
    "provider": "NASA POWER" | "Open-Meteo" | "IMD" | "ERA5",
    "observation_timestamp": "2010-06-15T12:00:00Z",
    "retrieved_timestamp": "2026-07-14T10:30:00Z",
    "age_seconds": 300,
    "confidence": 0.95,
    "data_source_identifier": "nasa_power_v2.3.8",
    "dataset_version": "1981-2011_archive_v1",
    "values": {
        "temperature_2m": 31.2,
        "precipitation_mm": 0.0
    }
}
```

This metadata is exposed through:
- Every dashboard card/chart/map/KPI
- Every Copilot tool response
- Every API endpoint response

---

## 3. Migration Strategy

### 3.1 Cascading Fallback (Anti-Fragile)

```
DataSourceManager.get_observation(location, variable, timestamp):
    │
    ├── LIVE: try providers in priority order
    │       ├── NASA POWER (priority 1)
    │       │   ├── Success → return LIVE
    │       │   └── Failure → retry (3x, exponential backoff)
    │       ├── Open-Meteo (priority 2)
    │       │   ├── Success → return LIVE
    │       │   └── Failure → retry (2x, exponential backoff)
    │       ├── IMD (priority 3)
    │       │   ├── Success → return LIVE
    │       │   └── Failure → circuit breaker opens
    │       └── All providers failed → fall through
    │
    ├── CACHED: check observation cache
    │       ├── Hit within TTL → return CACHED
    │       └── Miss → fall through
    │
    ├── HISTORICAL: check bundled archive
    │       ├── data/raw/rainfall.parquet matches location+date
    │       │   └── Match → return HISTORICAL
    │       └── No match → fall through
    │
    └── UNAVAILABLE: return status unavailable
```

**Never fail solely because the internet is unavailable.** Historical datasets are valid fallback data. Only return UNAVAILABLE if ALL four sources are exhausted for the specific (location, variable, timestamp) triple.

### 3.2 Auto-Build Training Data

When `data/processed/training.csv` is missing but `data/raw/*.parquet` exists:

```
models/data_loader.py:
    1. Check training.csv exists → load immediately
    2. Else check raw parquet exists → auto-build:
       a. Read rainfall.parquet, maxtemp.parquet, mintemp.parquet
       b. Join on (Date, Latitude, Longitude)
       c. Engineer features (Month, Week, Season, RollingRain7, etc.)
       d. Split into training/validation/testing
       e. Save to data/processed/
       f. Load and return
    3. Else raise descriptive configuration error
```

Never require manual preprocessing when the repository already contains raw data.

### 3.3 Copilot Data Policy

Copilot tools do NOT fabricate data and do NOT return simple "Service unavailable" errors. They use `DataSourceManager` exactly like the dashboard:

```
ForecastTool:
    result = DataSourceManager.get_forecast(location, days)
    if result.status == UNAVAILABLE:
        return "No verified climate observation is available for this location and time."
    else:
        return f"Showing {result.status} {result.provider} observation from {result.observation_timestamp}."
        # Include full provenance in response
```

### 3.4 SHAP Deferred to Phase 4

SHAP explainability (`risk/explainability/shap_explainer.py`) is deferred to Phase 4 (Scientific Improvements) because it depends on:
- Trained model checkpoints
- Model registry with supported explainers
- Working inference pipeline
- Real SHAP library integration (TreeExplainer, DeepExplainer, KernelExplainer)

Phase 1 only removes the heuristic (`_estimate_shap_values`) if it can be replaced with a hard "Model not available" response, but the SHAP file itself remains if it has structure needed later.

---

## 4. Phase Plan

### Phase 1: Remove Synthetic Production Code + Introduce DataSourceManager

**Objective:** No production code generates climate observations randomly. No consumer implements its own fallback logic.

**Actions:**

1. **Create `pipeline/providers/manager.py` — DataSourceManager**
   - Central authority for ALL climate data access
   - Implements cascading fallback (LIVE → CACHED → HISTORICAL → UNAVAILABLE)
   - Provider priority, retry, circuit breaker, cache lookup, historical lookup
   - Returns provenance metadata with every observation
   - Every consumer (dashboard, copilot, forecast, risk, scenario, twin) calls this

2. **Delete synthetic generators from `dashboard/services/api_client.py`:**
   - `_synthetic_forecast()` (lines 58-83)
   - `_synthetic_current_state()` (lines 86-107)
   - `_synthetic_risk()` (lines 110-135)
   - `_synthetic_scenario_result()` (lines 138-151)
   - `PREDEFINED_SCENARIOS` (lines 22-55)
   - Replace all fallback return paths with call to `DataSourceManager`

3. **Delete mock data from `dashboard/page_views/08_knowledge_base.py`:**
   - Remove `numpy` import
   - Remove all `np.random.seed/randint/uniform` calls (lines 13-28)
   - Replace mock results with real API call via knowledge service

4. **Delete mock data from `dashboard/page_views/09_feedback.py`:**
   - Remove `numpy` import
   - Remove `_generate_sample_feedback_data()` (lines 13-29)
   - Replace with real API call

5. **Delete mock data from `dashboard/page_views/10_twin_state_bhai.py`:**
   - Remove `numpy` import
   - Remove `_generate_sample_twin_data()` (lines 35-47)
   - Remove `_generate_sample_twin_history()` (lines 50-64)
   - Replace with real API call to twin-state-mgr

6. **Delete synthetic fallbacks from `copilot/tools/*.py` (6 files):**
   - `forecast_tool.py`: Delete `_synthetic_forecast()`. Replace fallback with DataSourceManager call.
   - `twin_tool.py`: Delete `_synthetic_twin_state()`. Replace fallback with DataSourceManager call.
   - `risk_tool.py`: Delete `_synthetic_risk()`. Replace fallback with DataSourceManager call.
   - `scenario_tool.py`: Delete `_synthetic_scenario()`. Replace fallback with DataSourceManager call.
   - `rag_tool.py`: Delete `_synthetic_rag()`. Replace fallback with DataSourceManager call.
   - `report_tool.py`: Delete `_synthetic_report()`. Replace fallback with DataSourceManager call.

7. **Delete synthetic generators from `pipeline/download.py`:**
   - `_generate_synthetic_rainfall()` (lines 44-67)
   - `_generate_synthetic_temperature()` (lines 69-98)
   - `_save_synthetic_rainfall()` (lines 131-144)
   - `_save_synthetic_temperature()` (lines 146-160)
   - Change `download_dataset()` to use DataSourceManager for fallback instead of synthetic generation

8. **Delete synthetic training data from `models/data_loader.py`:**
   - `_generate_synthetic_training_data()` (lines 97-147)
   - Replace with auto-build from historical parquet (see section 3.2)

9. **Delete synthetic forecast fallback from `backend/services/forecast/inference.py`:**
   - Remove `np.random.default_rng(42).uniform()` fallback (lines 107-111)
   - Replace with FileNotFoundError that guides user to run pipeline (not silent fabrication)

10. **Delete dummy embeddings from `knowledge/embeddings/embedding_model.py`:**
    - `_get_dummy_embedding()` (lines 22-28)
    - `_SimpleRNG` class (lines 31-39)
    - `_dummy_embedding_dim` (line 19)
    - `encode()` last resort → raise RuntimeError
    - `is_available()` → return True only when real model loaded

11. **Remove heuristic SHAP from `risk/explainability/shap_explainer.py`:**
    - `_estimate_shap_values()` (lines 84-107)
    - `generate_explanation()` without a model → raise error
    - Full SHAP integration deferred to Phase 4

**Verification:**
- `grep -r "np\.random" dashboard/ copilot/ backend/ pipeline/ models/ risk/ knowledge/ --include="*.py"` → only test files and non-production scripts
- `grep -r "_synthetic_" dashboard/ copilot/ pipeline/ models/ backend/ --include="*.py"` → zero matches
- `grep -r "dummy_embedding\|_get_dummy" knowledge/ --include="*.py"` → zero matches
- `grep -r "PREDEFINED_SCENARIOS" dashboard/ --include="*.py"` → zero matches

---

### Phase 2: Historical Data Integration

**Objective:** Load NASA POWER parquet into the Digital Twin. Every historical observation flows through StateManager → VersionedStateStore → Repository → EventBus. Historical data is exposed via DataSourceManager as HISTORICAL status.

**Actions:**

1. **Create `pipeline/import_historical.py`:**
   - Read `data/raw/rainfall.parquet`, `maxtemp.parquet`, `mintemp.parquet`
   - For each (date, lat, lon) triplet, create a `ClimateEntity`
   - Submit to `StateManager.update_state()` → `VersionedStateStore.save_state()` → `Repository.save_entity()`
   - Publish events via `EventBus.publish()`
   - Label all observations with `status: HISTORICAL`, `dataset_version: "1981-2011_archive_v1"`
   - Process in chunks with progress reporting

2. **Create `scripts/populate_twin.py`:**
   - Load config from YAML
   - Call historical importer
   - Verify version chain integrity
   - Print statistics (locations, records, date range)

3. **Add historical lookup to DataSourceManager:**
   - Load parquet metadata on startup
   - When LIVE and CACHED fail, query historical store
   - Return with `status: HISTORICAL`

4. **Create `tests/integration/test_historical_import.py`:**
   - Import a subset of parquet data (10 locations, 1 year)
   - Verify version count matches
   - Verify date range
   - Verify rollback works
   - Verify EventBus received expected events

---

### Phase 3: Live Provider Integration

**Objective:** ProviderManager operational with NASA POWER, Open-Meteo, IMD. Retry, circuit breaker, caching, scheduled refresh all working.

**Actions:**

1. **Create `pipeline/providers/base.py` — Provider base class:**
   ```python
   class BaseProvider(ABC):
       async def fetch(location, variable, timestamp) -> Observation
       def is_available() -> bool
       def health() -> ProviderHealth
   ```

2. **Update `pipeline/sources/nasa_power.py`:**
   - Wrap in `BaseProvider` interface
   - Add retry (3 attempts, 2s/4s/8s backoff)
   - Add timeout (30s)
   - Add schema validation
   - Add circuit breaker (5 failures → open 60s)

3. **Create `pipeline/sources/open_meteo.py`:**
   - Free API (no key required): `https://api.open-meteo.com/v1/forecast`
   - Support: temperature_2m, precipitation, relative_humidity_2m, surface_pressure, wind_speed_10m
   - Same retry/timeout/validation as NASA POWER

4. **Create `pipeline/providers/cache.py` — ObservationCache:**
   - Parquet-backed cache at `data/provider_cache/`
   - TTL-based eviction (configurable, default 24h)
   - Keyed on (location, variable, date)
   - `get()`, `save()`, `exists()`, `evict()`

5. **Wire DataSourceManager:**
   ```
   DataSourceManager.__init__():
       providers = [NASAPowerProvider, OpenMeteoProvider, IMDProvider]
       cache = ObservationCache("data/provider_cache")
       historical = HistoricalStore("data/raw/")
   
   DataSourceManager.get_observation(location, variable, timestamp):
       for provider in self.priority_order:
           try:
               obs = await provider.fetch(location, variable, timestamp)
               self.cache.save(obs)
               return obs.with_status(LIVE)
           except:
               continue
       
       cached = self.cache.get(location, variable, timestamp)
       if cached:
           return cached.with_status(CACHED)
       
       historical = self.historical.get(location, variable, timestamp)
       if historical:
           return historical.with_status(HISTORICAL)
       
       return Observation.unavailable(location, variable, timestamp)
   ```

6. **Update `config/data_config.yaml`** with provider configuration.

---

### Phase 4: Scientific Improvements

- Real SHAP implementation (TreeExplainer, DeepExplainer, KernelExplainer)
- Embedding model improvements (sentence-transformers mandatory, TF-IDF as fallback, no dummy)
- Model retraining on full historical dataset
- Cross-validation, checkpointing, evaluation metrics
- Model registry verification (MLP, LSTM, Transformer, PatchTST, TimeMixer, iTransformer)

---

### Phase 5: Production Hardening

- Structured logging (JSON)
- Metrics (prometheus_client)
- Auth/authorization
- HTTPS
- Rate limiting
- Health checks
- Graceful shutdown
- Docker health checks
- CI/CD pipeline

---

## 5. Files to Modify

### DELETE (synthetic generators — Phase 1)
- `dashboard/services/api_client.py` lines 22-55 (`PREDEFINED_SCENARIOS`)
- `dashboard/services/api_client.py` lines 58-151 (4 `_synthetic_*` functions)
- `dashboard/page_views/08_knowledge_base.py` lines 13-28 (np.random mock)
- `dashboard/page_views/09_feedback.py` lines 13-29 (`_generate_sample_feedback_data`)
- `dashboard/page_views/10_twin_state_bhai.py` lines 35-64 (2 `_generate_sample_twin_*` functions)
- `copilot/tools/forecast_tool.py` lines 37-67 (`_synthetic_forecast`)
- `copilot/tools/twin_tool.py` lines 14-26 (`_synthetic_twin_state`)
- `copilot/tools/risk_tool.py` lines 14-25 (`_synthetic_risk`)
- `copilot/tools/scenario_tool.py` lines 14-24 (`_synthetic_scenario`)
- `copilot/tools/report_tool.py` lines 66-90 (`_synthetic_report`)
- `copilot/tools/rag_tool.py` lines 67-87 (`_synthetic_rag`)
- `pipeline/download.py` lines 44-160 (4 synthetic generator functions)
- `models/data_loader.py` lines 97-147 (`_generate_synthetic_training_data`)
- `knowledge/embeddings/embedding_model.py` lines 19-39 (`_dummy_embedding_dim`, `_get_dummy_embedding`, `_SimpleRNG`)
- `risk/explainability/shap_explainer.py` lines 84-107 (`_estimate_shap_values`)

### MODIFY (replace fallback behavior — Phase 1)
- `dashboard/services/api_client.py` — all try/except blocks → DataSourceManager
- `dashboard/page_views/09_feedback.py` — `render()` → real API
- `backend/services/forecast/inference.py` — synthetic fallback → FileNotFoundError with guidance
- `knowledge/embeddings/embedding_model.py` — `encode()` last resort → RuntimeError
- All 6 copilot tools — try/except blocks → DataSourceManager

### CREATE (Phase 1)
- `pipeline/providers/manager.py` — `DataSourceManager`
- `pipeline/providers/base.py` — `BaseProvider` ABC
- `dashboard/components/data_source_indicator.py` — provenance badge component
- `tests/unit/test_datasource_manager.py` — DataSourceManager tests

### CREATE (Phase 2)
- `pipeline/import_historical.py` — Historical data importer
- `scripts/populate_twin.py` — Twin population script
- `tests/integration/test_historical_import.py` — Import tests

### CREATE (Phase 3)
- `pipeline/sources/open_meteo.py` — Open-Meteo provider
- `pipeline/providers/cache.py` — ObservationCache

---

## 6. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| NASA POWER API rate limits | Add delay between requests, batch grid points, use cache |
| Large parquet files slow Twin ingestion | Process in chunks (10k rows), show progress, commit periodically |
| DataSourceManager becomes a bottleneck | Stateless, no DB — just priority decision + cache lookup |
| Tests rely on synthetic fixtures | Replace with small HISTORICAL data samples from parquet |
| Copilot verbose with provenance | Template-based responses with clear source citation |
| FAISS build requires sentence-transformers | Add to Docker image, document in setup |
| Circuit breaker causes cascading unavailability | Per-provider breakers + historical fallback means data still flows |

---

## 7. Self-Review Checklist

| Check | Status | Notes |
|-------|--------|-------|
| No production synthetic climate data | ✓ | All synthetic generators removed in Phase 1 |
| Four runtime data states implemented | ✓ | LIVE, CACHED, HISTORICAL, UNAVAILABLE defined |
| DataSourceManager centralizes provider logic | ✓ | Every consumer calls it, none implement own fallback |
| Historical datasets separate from cache | ✓ | Distinct status, distinct badge, distinct storage |
| Auto-build processed data from raw parquet | ✓ | Section 3.2 specifies exact pipeline |
| SHAP deferred to Phase 4 | ✓ | Moved out of Phase 1 |
| Dashboard provenance metadata | ✓ | data_source_indicator component, 4-state badges |
| Copilot provenance metadata | ✓ | Copilot tools use DataSourceManager, cite source |
| No hard fails when historical data exists | ✓ | Cascading fallback means only return UNAVAILABLE when all 4 sources exhausted |
| No duplicate responsibilities | ✓ | DataSourceManager is sole authority for data access |
| No ambiguous behavior | ✓ | Every fallback path explicitly defined |
| No placeholder text | ✓ | All sections complete |
| No architectural regressions | ✓ | DigitalTwinEngine, EventBus, StateManager, Runtime all preserved |
| Consumers never implement provider logic | ✓ | All consumers call DataSourceManager |
