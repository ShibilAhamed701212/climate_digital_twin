# Phase 1 Implementation Specification — Real Data Foundation

**Date:** 2026-07-30
**Project:** Climate Digital Twin — ISRO BAH 2026 Challenge 5
**Status:** READY FOR REVIEW

---

## 0. Architecture Overview

```
CLI (pipeline/ingest.py)
  │  run_id = 20260730T120521Z_a83f21
  ▼
IngestionService
  │
  ├── DataSourceManager (provider resolution, priority, failover)
  │     ├── OpenMeteoProvider  → HTTP response
  │     ├── NASAPowerProvider  → HTTP response
  │     └── IMDStatus          → AUTH_REQUIRED
  │
  ├── RawDataStore (save raw HTTP response + metadata)
  │     └── data/real/raw/{provider}/{run_id}.json
  │
  ├── connector parser (list[WeatherObservation])
  │
  ├── adapter.py (WeatherObservation → Observation)
  │
  ├── validation (reuse existing pipeline/validate.py)
  │
  ├── ObservationStore (VALID observations)
  │     └── data/real/normalized/observations_{run_id}.parquet
  │
  ├── RejectedStore (REJECTED observations)
  │     └── data/real/rejected/rejected_{run_id}.parquet
  │
  └── ManifestWriter (run provenance)
        └── data/manifests/{run_id}.json
```

**Phase 1 ends here.** Phase 2 connects ObservationStore → TwinSynchronizer.

---

## 1. Exact Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `pipeline/ingest.py` | CLI entry point for real-data ingestion |
| 2 | `pipeline/ingestion_service.py` | IngestionService orchestrator |
| 3 | `pipeline/providers/adapter.py` | `WeatherObservation` → `Observation` centralized adapter |
| 4 | `pipeline/providers/fetch_result.py` | `FetchResult` envelope (success/failure) |
| 5 | `pipeline/providers/authenticity.py` | `DataAuthenticity` enum |
| 6 | `pipeline/providers/open_meteo_provider.py` | Sync `BaseProvider` wrapping `OpenMeteoConnector` |
| 7 | `pipeline/providers/nasa_power_provider.py` | Sync `BaseProvider` wrapping NASA POWER functions |
| 8 | `pipeline/providers/imd_status.py` | `AUTH_REQUIRED` provider stub |
| 9 | `pipeline/stores/raw_data_store.py` | `RawDataStore` — save raw HTTP responses before parsing |
| 10 | `pipeline/stores/observation_store.py` | `ObservationStore` — save/load/query validated Observations |
| 11 | `pipeline/stores/rejected_store.py` | `RejectedStore` — save rejected/dropped Observations |
| 12 | `pipeline/stores/manifest_writer.py` | `ManifestWriter` — ingestion run manifests |

### Data directories

| Path | Purpose |
|------|---------|
| `data/real/raw/open_meteo/` | Raw Open-Meteo HTTP responses |
| `data/real/raw/nasa_power/` | Raw NASA POWER HTTP responses |
| `data/real/normalized/` | Normalized parquet (post-adapter, pre-validation) |
| `data/real/validated/` | Validated parquet (post-validation, accepted) |
| `data/real/rejected/` | Rejected observations (post-validation, dropped) |
| `data/manifests/` | JSON manifests per run |

---

## 2. Exact Files to Modify

| # | File | Changes |
|---|------|---------|
| 1 | `pipeline/providers/manager.py` | Add `FORECAST` to `ObservationStatus`; wire provider list from config; update import of new enums |
| 2 | `pipeline/sources/openmeteo_connector.py` | Add unit normalization, schema validation, missing-value markers |
| 3 | `pipeline/sources/nasa_power.py` | Add retry (3 attempts, exponential backoff), HTML detection, timeout (30s), response validation |
| 4 | `pipeline/sources/imd_connector.py` | Return `AUTH_REQUIRED` status; document activation requirements; keep file as activation-ready stub |
| 5 | `config/data_config.yaml` | Add all 3 provider configs, provider priority, new data paths |
| 6 | `.env.example` | Add `REAL_DATA_DIR`, provider enable/disable flags |
| 7 | `pipeline/download.py` | Add header: `# LEGACY / SYNTHETIC / DEMO ONLY — Use pipeline/ingest.py for production` |
| 8 | `pipeline/run_pipeline.py` | Add same header; ensure it never auto-calls `pipeline/ingest.py` |

---

## 3. Classes and Interfaces to Introduce

### 3.1 `FetchResult` — `pipeline/providers/fetch_result.py`

```python
@dataclass
class FetchResult:
    provider: DataSource          # enum: OPEN_METEO, NASA_POWER, IMD
    status: Literal["SUCCESS", "FAILED"]
    observations: list[Observation]   # empty on FAILED
    error_code: str | None            # e.g. "RATE_LIMITED", "AUTH_REQUIRED"
    error_message: str | None
    requested_at: datetime
    completed_at: datetime
    request_metadata: dict            # provider, endpoint, params, coordinates, time range, HTTP status
```

**Key rule:** A failed provider request produces a `FetchResult` with `observations=[]`. Never produce `Observation` objects with "unavailable" values.

### 3.2 `ObservationStatus` (modified) — `pipeline/providers/manager.py`

```python
class ObservationStatus(enum.StrEnum):
    LIVE = "LIVE"           # Fresh from provider, current/recent time range
    CACHED = "CACHED"       # Previously fetched, within TTL
    HISTORICAL = "HISTORICAL"  # Bundled archive dataset
    FORECAST = "FORECAST"   # Future prediction from provider
    UNAVAILABLE = "UNAVAILABLE"  # No data from any source
```

Determined by what the observation **represents temporally**, not which provider:

| Scenario | Status |
|----------|--------|
| Open-Meteo response for current/recent hour | `LIVE` |
| Open-Meteo response for 2020 | `HISTORICAL` |
| Open-Meteo future prediction | `FORECAST` |
| NASA POWER archived observation | `HISTORICAL` |
| Observation loaded from cache | `CACHED` |
| All sources exhausted | `UNAVAILABLE` |

### 3.3 `DataAuthenticity` — `pipeline/providers/authenticity.py`

```python
class DataAuthenticity(enum.StrEnum):
    REAL = "REAL"           # Genuine external data from live provider or bundled archive
    SYNTHETIC = "SYNTHETIC" # Internally generated (test/demo only)
```

Independent of `ObservationStatus`. Valid combinations:

| Status | Authenticity | Meaning |
|--------|-------------|---------|
| `HISTORICAL` | `REAL` | NASA POWER 1981–2011 archive |
| `LIVE` | `REAL` | Open-Meteo current observation |
| `FORECAST` | `REAL` | Open-Meteo model prediction |
| `HISTORICAL` | `SYNTHETIC` | Legacy demo data (marked during migration) |
| `CACHED` | `REAL` | Previously fetched real data |

### 3.4 `Observation` provenance fields (enhanced)

The existing `Observation` model gains these fields:

| Field | Type | Example |
|-------|------|---------|
| `provider` | `DataSource` | `OPEN_METEO` |
| `source_dataset` | `str` | `"OPEN_METEO_FORECAST"`, `"ERA5"`, `"NASA_POWER"` |
| `authenticity` | `DataAuthenticity` | `REAL` |
| `observation_status` | `ObservationStatus` | `LIVE` |
| `run_id` | `str` | `"20260730T120521Z_a83f21"` |
| `schema_version` | `str` | `"1.0.0"` |

### 3.5 `IngestionService` — `pipeline/ingestion_service.py`

```python
class IngestionService:
    def __init__(self, config: dict):
        self.manager = DataSourceManager(config)
        self.raw_store = RawDataStore(config["data_dir"])
        self.obs_store = ObservationStore(config["data_dir"])
        self.rejected_store = RejectedStore(config["data_dir"])
        self.manifest_writer = ManifestWriter(config["data_dir"])
        self.adapter = ObservationAdapter()

    def run_single(
        self,
        variables: list[str],
        lat: float,
        lon: float,
        provider_override: str | None = None,
        intent: str = "recent",
    ) -> Manifest:
        run_id = generate_run_id()

        # 1. Resolve provider
        provider = self.manager.resolve_provider(variables, lat, lon, intent, provider_override)

        # 2. Fetch
        fetch_result = provider.fetch(variables, lat, lon)
        if fetch_result.status == "FAILED":
            return self._handle_failure(fetch_result, run_id)

        # 3. Save raw response
        self.raw_store.save(fetch_result.request_metadata, fetch_result.provider, run_id)

        # 4. Parse → WeatherObservation list (already inside fetch_result from connector)
        # 5. Adapter → Observation list
        observations = [self.adapter.to_observation(wo, provider, run_id) for wo in fetch_result.observations]

        # 6. Validate
        valid, rejected = validate_observations(observations)

        # 7. Store
        self.obs_store.save_batch(valid)
        self.rejected_store.save_batch(rejected)

        # 8. Write manifest
        manifest = self.manifest_writer.write(run_id, fetch_result, valid, rejected)
        return manifest
```

### 3.6 `ObservationStore` — `pipeline/stores/observation_store.py`

```python
class ObservationStore:
    def save(self, obs: Observation) -> str: ...
    def save_batch(self, observations: list[Observation]) -> int: ...
    def latest(self, variable: str, lat: float, lon: float) -> Observation | None: ...
    def query(self, variable: str, lat: float, lon: float,
              start: datetime, end: datetime) -> list[Observation]: ...
```

Implementation: parquet-backed (`data/real/normalized/`).

### 3.7 `RawDataStore` — `pipeline/stores/raw_data_store.py`

```python
class RawDataStore:
    def save(self, provider: DataSource, run_id: str,
             response_body: str, metadata: dict) -> str:
        # Save to data/real/raw/{provider}/{run_id}.json
        # Record: provider, endpoint, request params, coordinates,
        #         requested time range, HTTP status, retrieval timestamp,
        #         response SHA256
```

### 3.8 `ManifestWriter` — `pipeline/stores/manifest_writer.py`

```python
class ManifestWriter:
    def write(self, run_id: str, fetch_result: FetchResult,
              valid: list[Observation], rejected: list[Observation]) -> Manifest: ...

@dataclass
class Manifest:
    run_id: str
    provider: DataSource
    status: str
    requested_at: datetime
    completed_at: datetime
    records_received: int
    records_normalized: int
    records_validated: int
    records_rejected: int
    records_persisted: int
    synthetic_count: int
    error: str | None
    paths: dict[str, str]   # raw, normalized, validated, rejected, manifest
```

---

## 4. Existing Components to Reuse

| Component | Location | How Reused |
|-----------|----------|------------|
| `OpenMeteoConnector` | `pipeline/sources/openmeteo_connector.py` | Call `.fetch_historical()` / `.fetch_forecast()`, add unit normalization + schema validation |
| `DataSourceManager` | `pipeline/providers/manager.py` | Provider resolution, priority, failover logic — extended with new enums + provider wiring |
| `ValidationPipeline` | `pipeline/validate.py` | Reused as-is after adapter step |
| `WeatherObservation` | `simulator/models/weather.py` | Connector output (kept as domain model) |
| `Observation` | `simulator/models/imd.py` or equivalent DataSourceManager model | Adapter target (kept as provenance/persistence model) |
| `DataSource` enum | `simulator/models/weather.py` | Extended with provider values if missing |
| `QualityFlag` | `simulator/models/weather.py` | Reused as-is |
| `BaseProvider` | `pipeline/providers/base.py` | Sync wrapper interface for providers |
| `LocationRegistry` | `pipeline/sources/location_registry.py` | Reused for location lookups |

---

## 5. Data Schemas

### 5.1 `Observation` (adapter output)

```python
@dataclass
class Observation:
    observation_id: str           # uuid or hash
    run_id: str                   # ingestion run identifier
    provider: DataSource          # who supplied it
    source_dataset: str           # what underlying dataset/model
    authenticity: DataAuthenticity  # REAL or SYNTHETIC
    observation_status: ObservationStatus  # LIVE/CACHED/HISTORICAL/FORECAST/UNAVAILABLE
    latitude: float
    longitude: float
    observation_timestamp: datetime
    ingestion_timestamp: datetime
    values: dict[str, float]      # e.g. {"temperature_2m": 27.4, "humidity": 81.0}
    units: dict[str, str]         # e.g. {"temperature_2m": "°C", "humidity": "%"}
    quality_flag: QualityFlag     # VALID/SUSPECT/CORRECTED/REJECTED
    schema_version: str           # "1.0.0"
    additional_metadata: dict     # free-form provenance
```

### 5.2 `WeatherObservation` (unchanged, kept as connector domain model)

```python
# simulator/models/weather.py — no changes in Phase 1
```

### 5.3 Manifest JSON schema

```json
{
    "run_id": "20260730T120521Z_a83f21",
    "run_timestamp": "2026-07-30T12:05:21Z",
    "provider": "OPEN_METEO",
    "source_dataset": "OPEN_METEO_FORECAST",
    "intent": "recent",
    "location": {"lat": 12.9716, "lon": 77.5946},
    "status": "SUCCESS",
    "records_received": 24,
    "records_normalized": 24,
    "records_validated": 24,
    "records_rejected": 0,
    "records_persisted": 24,
    "synthetic_count": 0,
    "error": null,
    "paths": {
        "raw": "data/real/raw/open_meteo/20260730T120521Z_a83f21.json",
        "normalized": "data/real/normalized/observations_20260730T120521Z_a83f21.parquet",
        "validated": "data/real/validated/observations_20260730T120521Z_a83f21.parquet",
        "rejected": null,
        "manifest": "data/manifests/20260730T120521Z_a83f21.json"
    }
}
```

---

## 6. Provider Behavior

### 6.1 Provider Resolution

```
resolve_providers(variables, lat, lon, intent, override):
  if override:
    return [get_provider(override)]

  if intent == "forecast":
    priority = [OpenMeteoProvider]  # NASA POWER has no forecast API
  elif intent == "historical":
    priority = [NASAPowerProvider, OpenMeteoProvider]
  elif intent == "recent":
    priority = [OpenMeteoProvider, NASAPowerProvider]
  else:  # auto
    priority = [OpenMeteoProvider, NASAPowerProvider]

  IMD is NEVER tried unless explicitly configured (auth required)
```

### 6.2 Provider → Source Dataset Mapping

| Provider | Possible source_datasets |
|----------|------------------------|
| OPEN_METEO | `OPEN_METEO_FORECAST`, `ERA5` (via Open-Meteo ERA5 endpoint) |
| NASA_POWER | `NASA_POWER` |
| IMD | `IMD` |

Determined at runtime by what endpoint/API version returned the data.

### 6.3 Connector Enhancement Requirements

#### OpenMeteoConnector (`pipeline/sources/openmeteo_connector.py`)

- Add `normalize_units()`: convert all output to canonical units (°C, mm, %, hPa, km/h)
- Add `validate_schema()`: ensure all expected fields present, type-check values
- Add `mark_missing()`: replace `None` values with `float('nan')`, add missing-value metadata
- Existing aiohttp, retry, cache, rate limiting kept as-is

#### NASA POWER (`pipeline/sources/nasa_power.py`)

- Add retry: 3 attempts, exponential backoff (2s, 4s, 8s)
- Add HTML detection: check response Content-Type, reject HTML pages
- Add timeout: 30s default
- Add response validation: check for expected JSON structure before parsing
- Existing temporal range logic kept — do NOT hardcode to 1981–2011

#### IMD Connector (`pipeline/sources/imd_connector.py`)

- Replace fake base URL with `AUTH_REQUIRED` status
- Document activation requirements (API key, registration URL, expected endpoints)
- Keep file as stub for when credentials become available

### 6.4 Error Codes (FetchResult)

| Code | When |
|------|------|
| `SOURCE_UNAVAILABLE` | Provider endpoint unreachable or down |
| `REQUEST_FAILED` | HTTP error (4xx/5xx that isn't rate limit) |
| `AUTH_REQUIRED` | Provider requires authentication not configured |
| `RATE_LIMITED` | HTTP 429 or equivalent |
| `INVALID_RESPONSE` | Response received but not parseable (HTML, malformed JSON, wrong schema) |
| `NO_DATA` | Response valid but empty (no observations for requested parameters/location) |

---

## 7. Storage Structure

```
data/
├── real/
│   ├── raw/
│   │   ├── open_meteo/
│   │   │   └── {run_id}.json          # Full HTTP response body + metadata
│   │   └── nasa_power/
│   │       └── {run_id}.json
│   ├── normalized/
│   │   └── observations_{run_id}.parquet   # Post-adapter, pre-validation
│   ├── validated/
│   │   └── observations_{run_id}.parquet   # Post-validation, accepted
│   └── rejected/
│       └── rejected_{run_id}.parquet       # Post-validation, dropped
├── manifests/
│   └── {run_id}.json                       # Complete run provenance
├── raw/                                    # Existing synthetic (untouched)
│   ├── rainfall.parquet
│   ├── maxtemp.parquet
│   └── mintemp.parquet
├── processed/                              # Existing (untouched)
│   └── training.csv
└── synthetic/                              # New landing zone (in future)
```

**Existing `data/raw/` files are NOT moved.** They remain in place to avoid breaking existing models/tests. Their provenance will be marked as `SYNTHETIC` when read through DataSourceManager.

All NEW real data goes exclusively under `data/real/`.

---

## 8. Provenance Structure

Every observation carries:

| Field | Source | Example |
|-------|--------|---------|
| `observation_id` | Generated (uuid or hash) | `"a83f21b4-..."` |
| `run_id` | IngestionService | `"20260730T120521Z_a83f21"` |
| `provider` | Provider class | `OPEN_METEO` |
| `source_dataset` | Connector reports | `"OPEN_METEO_FORECAST"` |
| `authenticity` | Derived | `REAL` |
| `observation_status` | Derived from temporal meaning | `LIVE` |
| `latitude` | Request param | `12.9716` |
| `longitude` | Request param | `77.5946` |
| `observation_timestamp` | Provider response | `"2026-07-30T12:00:00Z"` |
| `ingestion_timestamp` | System clock | `"2026-07-30T12:05:21Z"` |
| `quality_flag` | Validation result | `VALID` |
| `schema_version` | Hardcoded | `"1.0.0"` |

Raw store records additional metadata:

| Field | Example |
|-------|---------|
| `provider` | `OPEN_METEO` |
| `endpoint` | `https://api.open-meteo.com/v1/forecast` |
| `request_params` | `{"latitude": 12.9716, "longitude": 77.5946, "hourly": "temperature_2m"}` |
| `http_status` | `200` |
| `retrieval_timestamp` | `"2026-07-30T12:05:20Z"` |
| `response_sha256` | `"abc123..."` |

---

## 9. Error and Failover Behavior

### 9.1 Production Failover Chain

```
Provider A fails (INVALID_RESPONSE)
  → Provider B fails (RATE_LIMITED)
    → Provider C fails (SOURCE_UNAVAILABLE)
      → report UNAVAILABLE in manifest
      → return to caller with explicit error
      → NEVER: synthetic generation
```

### 9.2 Failure Handling Rules

1. Every provider failure returns a `FetchResult(status="FAILED")` — never an `Observation`
2. `IngestionService` records the failure in the manifest with full error info
3. No `Observation` object is created for a failed request
4. No parquet file is created for an entirely failed run
5. CLI exit code is non-zero on complete failure
6. Only `UNAVAILABLE` in status — no fake data

### 9.3 Demo/Test Mode

`pipeline/ingest.py --demo-synthetic` enables synthetic generation for:
- Development environments
- Integration testing
- Demo/staging

Without `--demo-synthetic`, any synthetic generation is a runtime error.

---

## 10. CLI Behavior

### 10.1 Interface

```
python -m pipeline.ingest [OPTIONS]

Options:
  --lat FLOAT             Latitude (default: 12.9716)
  --lon FLOAT             Longitude (default: 77.5946)
  --variables LIST        Comma-separated variable names (default: all supported)
  --intent TEXT           recent | historical | forecast | auto (default: recent)
  --provider TEXT         open_meteo | nasa_power | imd | auto (default: auto)
  --demo-synthetic        Allow synthetic data generation (test/demo only)
  --output TEXT           Output format: text | json (default: text)
  --verbose               Detailed logging
```

### 10.2 Output (text mode)

```
╔══════════════════════════════════════════════════╗
║  Ingestion Run: 20260730T120521Z_a83f21         ║
╠══════════════════════════════════════════════════╣
║  Provider:        OPEN_METEO                     ║
║  Source Dataset:  OPEN_METEO_FORECAST            ║
║  Status:          LIVE                          ║
║  Authenticity:    REAL                          ║
║  Location:        12.9716, 77.5946              ║
║                                                  ║
║  Observation:     2026-07-30T12:00:00Z          ║
║  Ingestion:       2026-07-30T12:05:21Z          ║
║                                                  ║
║  Temperature:     27.4 °C                        ║
║  Humidity:        81.0 %                         ║
║  Rainfall:        4.2 mm                         ║
║  Pressure:        1008.2 hPa                     ║
║  Wind:            14.3 km/h @ 220°               ║
║                                                  ║
║  Records:         24 received, 24 validated, 0 rejected ║
║  Synthetic:       0                              ║
║                                                  ║
║  Saved:                                          ║
║    data/real/raw/open_meteo/20260730T120521Z...  ║
║    data/real/normalized/observations_20260730... ║
║    data/real/validated/observations_20260730...  ║
║    data/manifests/20260730T120521Z...json        ║
╚══════════════════════════════════════════════════╝
```

### 10.3 Output (json mode)

Standard JSON representation of the Manifest.

---

## 11. Unit Tests

### 11.1 `tests/unit/pipeline/test_ingestion_service.py`

- `test_run_single_success`: full run with mock Open-Meteo, verify manifest
- `test_run_single_provider_failure`: provider returns FETCH_FAILED, verify no observations persisted
- `test_run_single_all_providers_fail`: all fail → UNAVAILABLE, exit code 1
- `test_run_single_with_synthetic_flag`: synthetic mode works with flag, fails without
- `test_run_id_format`: verify run_id matches expected pattern
- `test_provider_resolution_override`: explicit provider override works
- `test_provider_resolution_auto`: auto mode picks correct provider per intent

### 11.2 `tests/unit/pipeline/test_fetch_result.py`

- `test_success_result`: observations populated, status SUCCESS
- `test_failure_result`: observations empty, error fields set
- `test_no_observation_for_failure`: failure never creates Observation objects

### 11.3 `tests/unit/pipeline/providers/test_adapter.py`

- `test_adapter_converts_weather_observation`: all fields mapped correctly
- `test_adapter_preserves_provenance`: provider, source, coordinates, timestamps preserved
- `test_adapter_handles_missing_values`: nan values passed through
- `test_adapter_generates_observation_id`: unique ID per call

### 11.4 `tests/unit/pipeline/stores/test_observation_store.py`

- `test_save_and_load`: save batch, load latest, verify fields
- `test_query_by_range`: query by time range returns correct records
- `test_query_no_results`: empty list for non-existent data
- `test_save_batch_count`: returns correct count

### 11.5 `tests/unit/pipeline/stores/test_raw_data_store.py`

- `test_save_raw_response`: file created with correct content
- `test_save_includes_metadata`: SHA256, timestamp, provider recorded

### 11.6 `tests/unit/pipeline/stores/test_manifest_writer.py`

- `test_write_manifest`: correct structure, all counts match
- `test_write_manifest_failure`: error field populated

### 11.7 `tests/unit/pipeline/providers/test_authenticity.py`

- `test_authenticity_values`: REAL and SYNTHETIC defined
- `test_authenticity_independent_from_status`: all valid combinations

### 11.8 `tests/unit/pipeline/providers/test_open_meteo_provider.py`

- (Adds to existing `test_openmeteo_connector.py`)
- `test_fetch_success`: returns FetchResult with SUCCESS
- `test_fetch_failure`: returns FetchResult with FAILED
- `test_fetch_no_synthetic_fallback`: failure returns empty observations

### 11.9 `tests/unit/pipeline/providers/test_nasa_power_provider.py`

- (Adds to existing `test_nasa_power.py`)
- `test_fetch_success`: returns FetchResult with SUCCESS
- `test_fetch_retry`: HTTP 429 triggers retry
- `test_fetch_html_detection`: HTML response → INVALID_RESPONSE
- `test_fetch_timeout`: timeout → REQUEST_FAILED

### 11.10 `tests/unit/pipeline/test_ingest_cli.py`

- `test_cli_help`: `--help` prints usage
- `test_cli_default_args`: default lat/lon used
- `test_cli_provider_override`: `--provider open_meteo` passed correctly
- `test_cli_demo_synthetic`: flag enables synthetic mode
- `test_cli_no_synthetic_without_flag`: error if synthetic attempted without flag

---

## 12. Integration Tests

### 12.1 `tests/integration/pipeline/test_full_ingestion.py`

- `test_ingest_open_meteo_recent`: Run `pipeline.ingest` with `--provider open_meteo --intent recent` against real API
  - Assert: exit code 0
  - Assert: manifest contains records_received > 0
  - Assert: raw file created at `data/real/raw/open_meteo/`
  - Assert: normalized parquet created at `data/real/normalized/`
  - Assert: validated parquet created at `data/real/validated/`
  - Assert: manifest created at `data/manifests/`
  - Assert: synthetic_count == 0

- `test_ingest_nasa_power_historical`: Run against NASA POWER API
  - Assert: success or appropriate error handled gracefully

- `test_ingest_all_providers`: Run with `--provider auto`
  - Assert: resolves and tries providers in correct priority

### 12.2 `tests/integration/pipeline/test_raw_to_persisted_roundtrip.py`

- Fetch real data, save raw, parse, adapt, validate, store
- Load from ObservationStore
- Assert: values match within floating-point tolerance

---

## 13. Real-Network Verification Procedure

Before claiming Phase 1 complete, run manually:

1. **Open-Meteo verification** (primary, easiest):
   ```bash
   python -m pipeline.ingest --provider open_meteo --intent recent --lat 12.9716 --lon 77.5946
   ```
   - [ ] Exit code 0
   - [ ] Temperature, humidity, rainfall, pressure, wind all populated
   - [ ] `synthetic_count: 0`
   - [ ] Files created in `data/real/raw/open_meteo/`, `data/real/normalized/`, `data/real/validated/`
   - [ ] Manifest readable

2. **Open-Meteo verification (forecast)**:
   ```bash
   python -m pipeline.ingest --provider open_meteo --intent forecast
   ```
   - [ ] Records received > 0
   - [ ] `observation_status: FORECAST` for future timestamps

3. **NASA POWER verification** (secondary):
   ```bash
   python -m pipeline.ingest --provider nasa_power --intent historical --lat 12.9716 --lon 77.5946
   ```
   - [ ] Request succeeds or returns clear error
   - [ ] If success: records > 0, `authenticity: REAL`, `observation_status: HISTORICAL`
   - [ ] If failure: `synthetic_count: 0`, clear error message, exit code may be non-zero

4. **IMD status check**:
   ```bash
   python -m pipeline.ingest --provider imd
   ```
   - [ ] Returns `AUTH_REQUIRED` — no attempt to hit API
   - [ ] Documents what's needed in error message

5. **Full auto run**:
   ```bash
   python -m pipeline.ingest
   ```
   - [ ] Resolves to Open-Meteo (recent)
   - [ ] Same checks as step 1

6. **Synthetic guard**:
   ```bash
   python -m pipeline.ingest --demo-synthetic --provider open_meteo
   ```
   - [ ] If Open-Meteo fails, synthetic data allowed
   - [ ] `synthetic_count > 0` if fallback triggered

   ```bash
   python -m pipeline.ingest --provider open_meteo  # no --demo-synthetic
   ```
   - [ ] If Open-Meteo fails, exits with error, no synthetic generation

7. **Legacy isolation**:
   ```bash
   python pipeline/download.py
   ```
   - [ ] Still works (unchanged) or warns LEGACY
   - [ ] Does NOT call `pipeline/ingest.py`

---

## 14. Definition of Done

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | `pipeline/ingest.py` is the canonical entry point for real data | `python -m pipeline.ingest --help` works |
| 2 | `DataSourceManager` resolves providers by priority + failover | Unit test covers all failover paths |
| 3 | `FetchResult` replaces `Observation.unavailable()` | No `Observation.unavailable()` in production path |
| 4 | `ObservationStatus` has LIVE/CACHED/HISTORICAL/FORECAST/UNAVAILABLE | Enum defined, tests pass |
| 5 | `DataAuthenticity` is separate from `ObservationStatus` | Enum defined, test covers valid combos |
| 6 | `provider` and `source_dataset` are separate provenance fields | Both present in Observation model |
| 7 | `RawDataStore` saves raw HTTP response BEFORE parsing | Raw file created before any transform |
| 8 | `ObservationStore` saves/loads | Unit test passes |
| 9 | `ManifestWriter` writes complete run manifest | Unit test passes |
| 10 | Every ingestion run has a unique `run_id` | IDs unique across runs |
| 11 | `pipeline/download.py` and `run_pipeline.py` marked LEGACY | Header comments present |
| 12 | All new real data goes under `data/real/` | No real data written to `data/raw/` |
| 13 | Synthetic generation requires `--demo-synthetic` flag | Test without flag fails, with flag works |
| 14 | Provider failures never produce fake Observations | Unit test: FetchResult failure → empty observations |
| 15 | NASA POWER does not hardcode 1981–2011 | Temporal range from provider config |
| 16 | Open-Meteo connector normalizes units | Unit test for each variable |
| 17 | NASA POWER connector has retry, HTML detection, timeout | Unit tests for each |
| 18 | IMD returns AUTH_REQUIRED | Integration check |
| 19 | All 10 provider error codes documented | Section 6.4 above |
| 20 | CLI text output matches spec format | Visual inspection |
| 21 | All unit tests pass | `python -m pytest tests/unit/pipeline/ -v` |
| 22 | Integration tests pass (or skipped for network) | `python -m pytest tests/integration/pipeline/ -v` |
| 23 | Real-network verification complete | All 7 steps in section 13 pass |
| 24 | No production code calls `download.py` synthetic generators | `grep` confirms zero callers |

---

## 15. Implementation Order

The implementation MUST follow this sequence to maintain a working codebase at each step:

| Step | Files | Why First |
|------|-------|-----------|
| **1** | `adapter.py`, `fetch_result.py`, `authenticity.py` | No dependencies — foundational types |
| **2** | Modify `pipeline/providers/manager.py` | Add enums, wire provider resolution |
| **3** | `raw_data_store.py`, `observation_store.py`, `rejected_store.py`, `manifest_writer.py` | Storage layer — depends only on types |
| **4** | Modify `openmeteo_connector.py`, `nasa_power.py` | Connector enhancements — reusable |
| **5** | `open_meteo_provider.py`, `nasa_power_provider.py`, `imd_status.py` | Sync wrappers — depends on connectors |
| **6** | `ingestion_service.py` | Orchestrator — depends on all above |
| **7** | `pipeline/ingest.py` | CLI — depends on IngestionService |
| **8** | Modify `config/data_config.yaml`, `.env.example` | Config — depends on knowing exact parameters |
| **9** | Modify `download.py`, `run_pipeline.py` headers | Mark LEGACY — last, no behavioral change |
| **10** | All unit tests | After implementation |
| **11** | All integration tests | After unit tests |
| **12** | Real-network verification | After all tests pass |
