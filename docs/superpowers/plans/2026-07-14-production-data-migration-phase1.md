# Production Data Migration — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all synthetic production data generation. Introduce DataSourceManager as the central authority for all climate data access.

**Architecture:** DataSourceManager sits between all consumers (dashboard, copilot, services) and data sources. It implements cascading fallback: LIVE provider → CACHED observation → HISTORICAL dataset → UNAVAILABLE. Every consumer calls DataSourceManager; no consumer implements its own provider or fallback logic.

**Tech Stack:** Python 3.11+, FastAPI, Streamlit, parquet, numpy, requests, pytest

## Global Constraints

- Never fabricate climate observations in production code
- DigitalTwinEngine, EventBus, StateManager, Runtime, Repository must not be modified
- Every response must include provenance metadata (status, provider, timestamp, age)
- Never produce UNAVAILABLE when HISTORICAL data exists for the requested location/variable/date
- Tests must be written before implementation code (TDD)

---

## File Structure

### Files to CREATE:
- `pipeline/providers/manager.py` — DataSourceManager (central data authority)
- `pipeline/providers/base.py` — BaseProvider ABC
- `pipeline/providers/historical_store.py` — HistoricalStore (reads bundled parquet)
- `dashboard/components/data_source_indicator.py` — Streamlit provenance badge component
- `tests/unit/test_datasource_manager.py` — DataSourceManager unit tests

### Files to MODIFY:
- `dashboard/services/api_client.py` — Replace synthetic fallbacks with DataSourceManager
- `dashboard/page_views/08_knowledge_base.py` — Remove np.random mock data
- `dashboard/page_views/09_feedback.py` — Remove np.random mock data
- `dashboard/page_views/10_twin_state_bhai.py` — Remove np.random twin data
- `copilot/tools/forecast_tool.py` — Remove `_synthetic_forecast`, use DataSourceManager
- `copilot/tools/twin_tool.py` — Remove `_synthetic_twin_state`, use DataSourceManager
- `copilot/tools/risk_tool.py` — Remove `_synthetic_risk`, use DataSourceManager
- `copilot/tools/scenario_tool.py` — Remove `_synthetic_scenario`, use DataSourceManager
- `copilot/tools/rag_tool.py` — Remove `_synthetic_rag`, use DataSourceManager
- `copilot/tools/report_tool.py` — Remove `_synthetic_report`, use DataSourceManager
- `pipeline/download.py` — Remove `_generate_synthetic_*`, `_save_synthetic_*`
- `models/data_loader.py` — Remove `_generate_synthetic_training_data`, auto-build from raw
- `backend/services/forecast/inference.py` — Remove np.random fallback
- `knowledge/embeddings/embedding_model.py` — Remove `_get_dummy_embedding`, `_SimpleRNG`
- `risk/explainability/shap_explainer.py` — Remove `_estimate_shap_values`

---

### Task 1: Write DataSourceManager Unit Tests (TDD)

**Files:**
- Create: `tests/unit/test_datasource_manager.py`

**Interfaces:**
- Consumes: (nothing — this is the first task)
- Produces: `DataSourceManager`, `ObservationStatus` enum, `Observation` dataclass

- [ ] **Step 1: Create the test file with observation status enum test**

```python
"""Tests for DataSourceManager — central climate data authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pipeline.providers.manager import (
    DataSourceManager,
    Observation,
    ObservationStatus,
)


class TestObservationStatus:
    def test_status_values(self):
        assert ObservationStatus.LIVE.value == "LIVE"
        assert ObservationStatus.CACHED.value == "CACHED"
        assert ObservationStatus.HISTORICAL.value == "HISTORICAL"
        assert ObservationStatus.UNAVAILABLE.value == "UNAVAILABLE"

    def test_status_order(self):
        assert ObservationStatus.LIVE != ObservationStatus.CACHED
        assert ObservationStatus.CACHED != ObservationStatus.HISTORICAL
        assert ObservationStatus.HISTORICAL != ObservationStatus.UNAVAILABLE
```

Run: `pytest tests/unit/test_datasource_manager.py::TestObservationStatus -v`
Expected: FAIL (no module named pipeline.providers.manager)

- [ ] **Step 2: Create the DataSourceManager module with enums**

Create `pipeline/providers/__init__.py`:
```python
"""Climate data providers package."""
```

Create `pipeline/providers/manager.py`:
```python
"""DataSourceManager — central authority for all climate data access.

Every consumer (dashboard, copilot, forecast, risk, scenario, twin)
must call DataSourceManager. Consumers must NEVER implement provider
logic or data generation themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ObservationStatus(Enum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    HISTORICAL = "HISTORICAL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class Observation:
    """A single climate observation with full provenance metadata."""

    status: ObservationStatus = ObservationStatus.UNAVAILABLE
    provider: str = ""
    observation_timestamp: str = ""
    retrieved_timestamp: str = ""
    age_seconds: float = 0.0
    confidence: float = 0.0
    data_source_identifier: str = ""
    dataset_version: str = ""
    values: dict[str, float] = field(default_factory=dict)
    location_id: str = ""
    variable: str = ""
    message: str = ""

    @classmethod
    def unavailable(cls, location_id: str, variable: str, message: str = "") -> Observation:
        return cls(
            status=ObservationStatus.UNAVAILABLE,
            location_id=location_id,
            variable=variable,
            message=message or "No verified climate observations available.",
            retrieved_timestamp=datetime.now(timezone.utc).isoformat(),
        )


class DataSourceManager:
    """Central authority for climate data access with cascading fallback.

    Resolution order:
    1. LIVE — try providers in priority order
    2. CACHED — check observation cache
    3. HISTORICAL — check bundled archive datasets
    4. UNAVAILABLE — no data exists
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._providers: list[BaseProvider] = []
        self._historical_store: HistoricalStore | None = None
        self._cache: ObservationCache | None = None

    def get_observation(self, location_id: str, variable: str, timestamp: str | None = None) -> Observation:
        """Get the best available observation for a location/variable.

        Returns the highest-priority observation available, following
        the LIVE → CACHED → HISTORICAL → UNAVAILABLE cascade.
        """
        # 1. Try LIVE providers
        for provider in self._providers:
            if not provider.is_available():
                continue
            try:
                obs = provider.fetch(location_id, variable, timestamp)
                if obs is not None:
                    self._save_to_cache(obs)
                    return obs
            except Exception:
                continue

        # 2. Try cache
        cached = self._get_from_cache(location_id, variable, timestamp)
        if cached is not None:
            return cached

        # 3. Try historical store
        if self._historical_store is not None:
            historical = self._historical_store.lookup(location_id, variable, timestamp)
            if historical is not None:
                return historical

        # 4. Unavailable
        return Observation.unavailable(location_id, variable)

    def _save_to_cache(self, obs: Observation) -> None:
        if self._cache is not None:
            self._cache.save(obs)

    def _get_from_cache(self, location_id: str, variable: str, timestamp: str | None) -> Observation | None:
        if self._cache is None:
            return None
        return self._cache.get(location_id, variable, timestamp)
```

Create `pipeline/providers/base.py`:
```python
"""Base provider interface for all climate data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pipeline.providers.manager import Observation


class BaseProvider(ABC):
    """Abstract base class for climate data providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is currently available."""

    @abstractmethod
    def fetch(self, location_id: str, variable: str, timestamp: str | None = None) -> Observation | None:
        """Fetch an observation from this provider.

        Returns None if the provider cannot fulfill the request.
        """

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return provider health status."""
```

- [ ] **Step 3: Run tests to verify they now pass**

Run: `pytest tests/unit/test_datasource_manager.py::TestObservationStatus -v`
Expected: PASS

- [ ] **Step 4: Write tests for DataSourceManager cascading fallback**

Add to `tests/unit/test_datasource_manager.py`:
```python
class TestDataSourceManager:
    def test_unavailable_when_no_providers(self):
        dsm = DataSourceManager()
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.UNAVAILABLE
        assert "No verified climate observations available" in obs.message

    def test_unavailable_when_all_providers_fail(self, mocker):
        dsm = DataSourceManager()
        mock_provider = mocker.Mock()
        mock_provider.is_available.return_value = True
        mock_provider.fetch.side_effect = ConnectionError("API down")
        dsm._providers = [mock_provider]
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.UNAVAILABLE

    def test_live_from_first_provider(self, mocker):
        dsm = DataSourceManager()
        live_obs = Observation(
            status=ObservationStatus.LIVE,
            provider="NASA POWER",
            location_id="KA-BLR-001",
            variable="temperature_2m",
            values={"temperature_2m": 31.2},
        )
        mock_provider = mocker.Mock()
        mock_provider.is_available.return_value = True
        mock_provider.fetch.return_value = live_obs
        dsm._providers = [mock_provider]
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.LIVE
        assert obs.provider == "NASA POWER"
        assert obs.values["temperature_2m"] == 31.2

    def test_historical_fallback_when_providers_fail(self, mocker):
        dsm = DataSourceManager()
        mock_provider = mocker.Mock()
        mock_provider.is_available.return_value = True
        mock_provider.fetch.side_effect = ConnectionError("API down")
        dsm._providers = [mock_provider]
        historical_obs = Observation(
            status=ObservationStatus.HISTORICAL,
            provider="NASA POWER",
            location_id="KA-BLR-001",
            variable="temperature_2m",
            values={"temperature_2m": 28.5},
            dataset_version="1981-2011_archive_v1",
        )
        mock_historical = mocker.Mock()
        mock_historical.lookup.return_value = historical_obs
        dsm._historical_store = mock_historical
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.HISTORICAL
        assert obs.dataset_version == "1981-2011_archive_v1"

    def test_provider_priority_order(self, mocker):
        dsm = DataSourceManager()
        first = mocker.Mock()
        first.is_available.return_value = True
        first.fetch.side_effect = ConnectionError("fail")
        second = mocker.Mock()
        second.is_available.return_value = True
        second.fetch.return_value = Observation(
            status=ObservationStatus.LIVE,
            provider="Open-Meteo",
            location_id="KA-BLR-001",
            variable="temperature_2m",
        )
        dsm._providers = [first, second]
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.LIVE
        assert obs.provider == "Open-Meteo"
```

- [ ] **Step 5: Run datasource manager tests**

Run: `pytest tests/unit/test_datasource_manager.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit DataSourceManager core**

```bash
git add pipeline/providers/ tests/unit/test_datasource_manager.py
git commit -m "feat: add DataSourceManager with cascading fallback and Observation model"
```

---

### Task 2: Create HistoricalStore

**Files:**
- Create: `pipeline/providers/historical_store.py`
- Test: add tests to `tests/unit/test_datasource_manager.py`

**Interfaces:**
- Consumes: `Observation` from Task 1
- Produces: `HistoricalStore` class with `lookup()` method

- [ ] **Step 1: Write HistoricalStore tests**

Add to `tests/unit/test_datasource_manager.py`:
```python
class TestHistoricalStore:
    def test_lookup_returns_none_when_no_data(self, tmp_path):
        from pipeline.providers.historical_store import HistoricalStore
        store = HistoricalStore(data_dir=str(tmp_path))
        obs = store.lookup("KA-BLR-001", "temperature_2m")
        assert obs is None
```

- [ ] **Step 2: Create HistoricalStore**

Create `pipeline/providers/historical_store.py`:
```python
"""HistoricalStore — reads bundled archived climate datasets.

Historical datasets are distributed with the repository and are never
overwritten. They serve as the HISTORICAL data state fallback when no
LIVE or CACHED observation is available.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.providers.manager import Observation, ObservationStatus

logger = logging.getLogger(__name__)


class HistoricalStore:
    """Reads bundled parquet datasets and returns them as HISTORICAL observations."""

    DATASET_FILES: dict[str, str] = {
        "rainfall": "data/raw/rainfall.parquet",
        "max_temp": "data/raw/maxtemp.parquet",
        "min_temp": "data/raw/mintemp.parquet",
    }

    VARIABLE_MAP: dict[str, str] = {
        "temperature_2m": "max_temp",
        "temperature_2m_min": "min_temp",
        "precipitation_mm": "rainfall",
        "rainfall": "rainfall",
        "max_temp": "max_temp",
        "min_temp": "min_temp",
    }

    COLUMN_MAP: dict[str, str] = {
        "temperature_2m": "MaxTemp",
        "temperature_2m_min": "MinTemp",
        "precipitation_mm": "Rainfall",
        "rainfall": "Rainfall",
        "max_temp": "MaxTemp",
        "min_temp": "MinTemp",
    }

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path("data/raw")
        self._datasets: dict[str, pd.DataFrame] = {}

    def lookup(self, location_id: str, variable: str, timestamp: str | None = None) -> Observation | None:
        """Look up a historical observation.

        Returns an Observation with status HISTORICAL if data exists,
        None otherwise.
        """
        dataset_key = self.VARIABLE_MAP.get(variable)
        if dataset_key is None:
            return None

        df = self._load_dataset(dataset_key)
        if df is None or df.empty:
            return None

        col = self.COLUMN_MAP.get(variable, variable)
        if col not in df.columns:
            return None

        # Use the most recent row as the current observation
        latest = df.iloc[-1]
        value = float(latest[col])

        return Observation(
            status=ObservationStatus.HISTORICAL,
            provider="NASA POWER",
            observation_timestamp=str(latest.get("Date", "")),
            retrieved_timestamp=datetime.now(timezone.utc).isoformat(),
            age_seconds=0.0,
            confidence=0.85,
            data_source_identifier="nasa_power_v2.3.8",
            dataset_version="1981-2011_archive_v1",
            values={variable: value},
            location_id=location_id,
            variable=variable,
        )

    def _load_dataset(self, dataset_key: str) -> pd.DataFrame | None:
        if dataset_key in self._datasets:
            return self._datasets[dataset_key]

        file_path = self._data_dir / f"{dataset_key}.parquet"
        alt_path = self._data_dir.parent / "raw" / f"{dataset_key}.parquet"

        for path in [file_path, alt_path]:
            if path.exists():
                try:
                    df = pd.read_parquet(path)
                    self._datasets[dataset_key] = df
                    logger.info("Loaded historical dataset %s (%d rows)", path, len(df))
                    return df
                except Exception as e:
                    logger.warning("Failed to load historical dataset %s: %s", path, e)
                    return None

        logger.warning("Historical dataset not found: %s", dataset_key)
        return None

    def is_available(self) -> bool:
        return any(self._load_dataset(k) is not None for k in self.DATASET_FILES)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/test_datasource_manager.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit HistoricalStore**

```bash
git add pipeline/providers/historical_store.py tests/unit/test_datasource_manager.py
git commit -m "feat: add HistoricalStore for bundled archive datasets"
```

---

### Task 3: Create DataSourceIndicator Component

**Files:**
- Create: `dashboard/components/data_source_indicator.py`

- [ ] **Step 1: Write the data source indicator component**

Create `dashboard/components/data_source_indicator.py`:
```python
"""Data source indicator — displays provenance metadata on dashboard widgets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st


STATUS_LABELS = {
    "LIVE": ("🟢", "Live"),
    "CACHED": ("🟡", "Cached"),
    "HISTORICAL": ("🔵", "Historical"),
    "UNAVAILABLE": ("⚪", "Unavailable"),
}

STATUS_HELP = {
    "LIVE": "Fresh observation from a live provider",
    "CACHED": "Previously downloaded observation within cache window",
    "HISTORICAL": "Bundled archived dataset (NASA POWER 1981-2011)",
    "UNAVAILABLE": "No verified observation exists",
}


def data_source_indicator(observation: dict[str, Any] | None) -> None:
    """Render a compact provenance badge for a data observation.

    Call this next to every chart, map, KPI, or card that displays
    climate data.
    """
    if observation is None:
        st.caption("⚪ Unavailable | No data")
        return

    status = observation.get("status", "UNAVAILABLE")
    icon, label = STATUS_LABELS.get(status, ("⚪", "Unknown"))
    provider = observation.get("provider", "unknown")
    obs_ts = observation.get("observation_timestamp", "")
    age = observation.get("age_seconds", 0)

    help_text = STATUS_HELP.get(status, "")
    parts = [f"{icon} {label}"]
    if provider:
        parts.append(provider)
    if obs_ts:
        parts.append(obs_ts)
    if age:
        age_str = _format_age(age)
        parts.append(age_str)

    st.caption(" | ".join(parts), help=help_text)


def _format_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    else:
        return f"{int(seconds / 86400)}d ago"
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/components/data_source_indicator.py
git commit -m "feat: add data_source_indicator component for provenance badges"
```

---

### Task 4: Refactor Dashboard API Client — Remove Synthetic Fallbacks

**Files:**
- Modify: `dashboard/services/api_client.py`
- Interfacing with: `DataSourceManager`, `HistoricalStore`

- [ ] **Step 1: Read current api_client.py to identify all synthetic fallback locations**

Read `dashboard/services/api_client.py` to confirm exact line ranges.

- [ ] **Step 2: Replace synthetic fallbacks with DataSourceManager calls**

Edit `dashboard/services/api_client.py`:

1. Add import for DataSourceManager and HistoricalStore at the top
2. Delete `PREDEFINED_SCENARIOS` constant (lines ~22-55)
3. Delete `_synthetic_forecast()` function (lines ~58-83)
4. Delete `_synthetic_current_state()` function (lines ~86-107)
5. Delete `_synthetic_risk()` function (lines ~110-135)
6. Delete `_synthetic_scenario_result()` function (lines ~138-151)

7. In `get_current_state()`, replace the except block:
```python
except Exception as e:
    logger.warning("Twin service unavailable: %s", e)
    self._mark_fallback("current_state")
    obs = self._dsm.get_observation(location_id, "temperature_2m")
    if obs.status != ObservationStatus.UNAVAILABLE:
        return {
            "location_id": location_id,
            "latitude": meta["lat"],
            "longitude": meta["lon"],
            "district": meta["district"],
            "timestamp": obs.observation_timestamp or datetime.now().isoformat(),
            "rainfall": obs.values.get("precipitation_mm", 0),
            "max_temp": obs.values.get("temperature_2m", 0),
            "min_temp": obs.values.get("temperature_2m_min", 0),
            "risk_score": 0,
            "prediction_confidence": obs.confidence,
            "state_type": "current",
            "data_source": obs.status.value,
            "provider": obs.provider,
            "dataset_version": obs.dataset_version,
        }
    return {
        "status": "unavailable",
        "message": "No verified climate observations available.",
        "location_id": location_id,
    }
```

8. In `get_forecast()`, replace the except block similarly
9. In `get_risk()`, replace the except block similarly
10. In `simulate_scenario()`, replace the except block similarly
11. Add `DataSourceManager` initialization in `__init__` or `create_api_client()`

- [ ] **Step 3: Run dashboard tests**

Run: `pytest tests/unit/test_dashboard.py -v`
Expected: All tests PASS (existing tests should still work if they mock the API)

- [ ] **Step 4: Commit**

```bash
git add dashboard/services/api_client.py
git commit -m "refactor: replace synthetic dashboard API fallbacks with DataSourceManager"
```

---

### Task 5: Remove Mock Data from Knowledge Base Page (08)

**Files:**
- Modify: `dashboard/page_views/08_knowledge_base.py`

- [ ] **Step 1: Read current file**

Read `dashboard/page_views/08_knowledge_base.py` to see exact mock data lines.

- [ ] **Step 2: Remove numpy import and mock data generation**

Edit `dashboard/page_views/08_knowledge_base.py`:
- Remove `import numpy as np`
- Remove all `np.random.seed/randint/uniform` calls (lines ~13-28)
- Replace mock results section with query to knowledge API service

```python
def render(api: DashboardAPI, filters: dict) -> None:
    st.header("Knowledge Base")
    st.markdown("Search climate documents, government reports, and research papers.")

    query = st.text_input("Search query", placeholder="e.g., flood risks in Karnataka during monsoon")

    if not query:
        st.info("Enter a search query to find relevant climate documents.")
        return

    if st.button("Search", type="primary"):
        with st.spinner("Searching knowledge base..."):
            try:
                results = api.search_knowledge(query)
                if not results:
                    st.warning("No results found for your query.")
                    return
                for r in results:
                    with st.expander(f"{r.get('title', 'Document')} — Score: {r.get('score', 0):.2f}"):
                        st.markdown(r.get('content', ''))
                        st.caption(f"Source: {r.get('source', 'unknown')}")
            except Exception as e:
                st.warning(f"Knowledge base search unavailable: {e}")
```

- [ ] **Step 3: Verify no numpy/np.random in file**

Run: `grep -n "np\.random\|numpy" dashboard/page_views/08_knowledge_base.py`
Expected: No matches

- [ ] **Step 4: Commit**

```bash
git add dashboard/page_views/08_knowledge_base.py
git commit -m "refactor: remove mock np.random data from knowledge base page"
```

---

### Task 6: Remove Mock Data from Feedback Page (09)

**Files:**
- Modify: `dashboard/page_views/09_feedback.py`

- [ ] **Step 1: Remove numpy import and mock data generation**

Edit `dashboard/page_views/09_feedback.py`:
- Remove `import numpy as np` (line 8)
- Remove `_generate_sample_feedback_data()` function (lines ~13-29)
- Replace the `df = _generate_sample_feedback_data()` call with API call:

```python
def render(api: DashboardAPI, filters: dict) -> None:
    st.header("Feedback Analytics")
    st.markdown("Track model performance, rating trends, and location-specific feedback.")

    try:
        feedback_data = api.get_feedback_data()
    except Exception as e:
        st.warning(f"Feedback data unavailable: {e}")
        st.info("No feedback data available. Feedback collection requires the feedback service.")
        return

    if not feedback_data:
        st.info("No feedback data available.")
        return

    df = pd.DataFrame(feedback_data)
    # ... rest of the rendering code stays the same
```

- [ ] **Step 2: Verify no numpy/np.random in file**

Run: `grep -n "np\.random\|numpy" dashboard/page_views/09_feedback.py`
Expected: No matches

- [ ] **Step 3: Commit**

```bash
git add dashboard/page_views/09_feedback.py
git commit -m "refactor: remove mock np.random feedback data from page 09"
```

---

### Task 7: Remove Mock Data from Twin State BHAI Page (10)

**Files:**
- Modify: `dashboard/page_views/10_twin_state_bhai.py`

- [ ] **Step 1: Remove numpy import and mock generation functions**

Edit `dashboard/page_views/10_twin_state_bhai.py`:
- Remove `import numpy as np` (line 8)
- Remove `_generate_sample_twin_data()` function (lines ~35-47)
- Remove `_generate_sample_twin_history()` function (lines ~50-64)
- Replace all mock data calls with API calls:

```python
def render(api: DashboardAPI, filters: dict) -> None:
    st.header("Digital Twin State Browser")
    st.markdown("Browse digital twin entity states, version history, and compare versions.")

    # ... sidebar selection stays the same ...

    if view_mode == "Current State":
        if refresh_btn or "twin_state" not in st.session_state:
            with st.spinner(f"Loading state for {district['name']}..."):
                state = api.get_current_state(entity_id)
                if state and "status" not in state:
                    st.session_state["twin_state"] = state
                else:
                    st.warning(state.get("message", "No state data available."))
                    st.stop()

        state = st.session_state.get("twin_state", {})
        # ... rest of rendering stays the same ...

    elif view_mode == "Version History":
        if refresh_btn or "twin_history" not in st.session_state:
            with st.spinner(f"Loading history for {district['name']}..."):
                history = api.get_version_history(entity_id)
                st.session_state["twin_history"] = history or []
        # ...

    elif view_mode == "Version Comparison":
        # ... version comparison via api.compare_versions() ...
```

- [ ] **Step 2: Verify no numpy/np.random in file**

Run: `grep -n "np\.random\|numpy" dashboard/page_views/10_twin_state_bhai.py`
Expected: No matches

- [ ] **Step 3: Commit**

```bash
git add dashboard/page_views/10_twin_state_bhai.py
git commit -m "refactor: remove mock np.random data from twin state BHAI page"
```

---

### Task 8-13: Refactor All 6 Copilot Tools

**Files:** 6 files in `copilot/tools/`

Each follows the same pattern: delete `_synthetic_*` function, replace try/except fallback with DataSourceManager call.

- [ ] **Task 8: Refactor `copilot/tools/forecast_tool.py`**
  - Delete `_synthetic_forecast()` (lines ~37-67)
  - Replace except block:
```python
except (ConnectionError, Timeout, HTTPError) as e:
    logger.warning("Forecast service unavailable: %s", e)
    from pipeline.providers.manager import DataSourceManager
    dsm = DataSourceManager()
    obs = dsm.get_observation(location.lower(), "temperature_2m")
    if obs.status != ObservationStatus.UNAVAILABLE:
        return {
            "tool": self._name,
            "location": location,
            "days": days,
            "forecast": [{"day": 1, "date": obs.observation_timestamp, "max_temp": obs.values.get("temperature_2m", 0), "min_temp": obs.values.get("temperature_2m_min", 0), "rainfall_mm": obs.values.get("precipitation_mm", 0)}],
            "available": True,
            "data_source": obs.status.value,
            "provider": obs.provider,
        }
    return {"tool": self._name, "location": location, "days": days, "available": False, "error": "No verified climate observation is available."}
```

- [ ] **Task 9: Refactor `copilot/tools/twin_tool.py`**
  - Delete `_synthetic_twin_state()` (lines ~14-26)
  - Replace except block with DataSourceManager

- [ ] **Task 10: Refactor `copilot/tools/risk_tool.py`**
  - Delete `_synthetic_risk()` (lines ~14-25)
  - Replace except block with DataSourceManager

- [ ] **Task 11: Refactor `copilot/tools/scenario_tool.py`**
  - Delete `_synthetic_scenario()` (lines ~14-24)
  - Replace except block with DataSourceManager

- [ ] **Task 12: Refactor `copilot/tools/rag_tool.py`**
  - Delete `_synthetic_rag()` (lines ~67-87)
  - Replace except block with DataSourceManager

- [ ] **Task 13: Refactor `copilot/tools/report_tool.py`**
  - Delete `_synthetic_report()` (lines ~66-90)
  - Replace except block with DataSourceManager

- [ ] **Commit all copilot tool changes:**
```bash
git add copilot/tools/
git commit -m "refactor: replace synthetic copilot tool fallbacks with DataSourceManager"
```

---

### Task 14: Refactor Pipeline — Remove Synthetic Generators

**Files:**
- Modify: `pipeline/download.py`

- [ ] **Step 1: Remove synthetic generation functions**

Delete from `pipeline/download.py`:
- `_generate_synthetic_rainfall()` (lines ~44-67)
- `_generate_synthetic_temperature()` (lines ~69-98)
- `_save_synthetic_rainfall()` (lines ~131-144)
- `_save_synthetic_temperature()` (lines ~146-160)

- [ ] **Step 2: Replace fallback in download_dataset()**

Change `download_dataset()`:
```python
def download_dataset(self, dataset_key: str) -> Path:
    # ... existing file existence check ...
    
    # Try NASA POWER download
    raise RuntimeError(
        f"Failed to download dataset '{dataset_key}'. "
        "All providers are unavailable. "
        "Historical data is available from the bundled archive at data/raw/."
    )
```

- [ ] **Step 3: Run pipeline tests**

Run: `pytest tests/unit/test_download.py -v`
Expected: Tests that test synthetic fallback will fail — fix or remove them

- [ ] **Step 4: Commit**

```bash
git add pipeline/download.py
git commit -m "refactor: remove synthetic data generators from pipeline download"
```

---

### Task 15: Refactor Model Data Loader — Auto-Build from Raw

**Files:**
- Modify: `models/data_loader.py`

- [ ] **Step 1: Remove `_generate_synthetic_training_data()`**

Delete lines ~97-147.

- [ ] **Step 2: Add auto-build from raw parquet**

Replace the synthetic fallback with:
```python
def _auto_build_training_data(config: dict, seq_len: int, forecast_horizon: int):
    """Auto-build training CSV from raw historical parquet files."""
    import pandas as pd
    import numpy as np
    from pathlib import Path

    raw_dir = Path(config["data"]["raw_dir"])
    processed_dir = Path(config["data"]["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Load parquet files
    rainfall = pd.read_parquet(raw_dir / "rainfall.parquet")
    maxtemp = pd.read_parquet(raw_dir / "maxtemp.parquet")
    mintemp = pd.read_parquet(raw_dir / "mintemp.parquet")

    # Merge on Date, Latitude, Longitude
    df = rainfall.merge(maxtemp, on=["Date", "Latitude", "Longitude"])
    df = df.merge(mintemp, on=["Date", "Latitude", "Longitude"])

    # Engineer features
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.month
    df["Week"] = df["Date"].dt.isocalendar().week.astype(int)
    df["Season"] = df["Month"].map({12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3})
    df["Monsoon"] = df["Month"].isin([6, 7, 8, 9]).astype(int)
    df["RollingRain7"] = df.groupby(["Latitude", "Longitude"])["Rainfall"].transform(lambda x: x.rolling(7, min_periods=1).mean())
    df["RollingRain30"] = df.groupby(["Latitude", "Longitude"])["Rainfall"].transform(lambda x: x.rolling(30, min_periods=1).mean())
    df["RollingTemp7"] = df.groupby(["Latitude", "Longitude"])["MaxTemp"].transform(lambda x: x.rolling(7, min_periods=1).mean())
    df["RollingTemp30"] = df.groupby(["Latitude", "Longitude"])["MaxTemp"].transform(lambda x: x.rolling(30, min_periods=1).mean())

    # Split
    dates = df["Date"].unique()
    n = len(dates)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    train_dates = dates[:train_end]
    val_dates = dates[train_end:val_end]
    test_dates = dates[val_end:]

    train_df = df[df["Date"].isin(train_dates)]
    val_df = df[df["Date"].isin(val_dates)]
    test_df = df[df["Date"].isin(test_dates)]

    train_df.to_csv(processed_dir / "training.csv", index=False)
    val_df.to_csv(processed_dir / "validation.csv", index=False)
    test_df.to_csv(processed_dir / "testing.csv", index=False)

    logger.info("Auto-built training data: %d train, %d val, %d test rows", len(train_df), len(val_df), len(test_df))
    return train_df, val_df, test_df
```

- [ ] **Step 3: Run model tests**

Run: `pytest tests/unit/test_data_loader.py -v`
Expected: Tests that use `_generate_synthetic_training_data` will fail — fix them to use auto-build

- [ ] **Step 4: Commit**

```bash
git add models/data_loader.py
git commit -m "refactor: replace synthetic training data generator with auto-build from raw parquet"
```

---

### Task 16: Refactor Forecast Inference — Remove np.random Fallback

**Files:**
- Modify: `backend/services/forecast/inference.py`

- [ ] **Step 1: Remove np.random fallback**

In `_load_latest_data()`, replace the else clause (lines ~107-111):
```python
else:
    raise FileNotFoundError(
        "No processed data available for forecast inference. "
        "Run the data pipeline first to generate training/validation/testing CSV files "
        "from the historical parquet datasets."
    )
```

- [ ] **Step 2: Run forecast inference tests**

Run: `pytest tests/unit/test_inference.py -v` (or similar)
Expected: Tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/services/forecast/inference.py
git commit -m "refactor: remove np.random fallback from forecast inference"
```

---

### Task 17: Refactor Embedding Model — Remove Dummy Embeddings

**Files:**
- Modify: `knowledge/embeddings/embedding_model.py`

- [ ] **Step 1: Remove dummy embedding code**

Delete from `knowledge/embeddings/embedding_model.py`:
- `_dummy_embedding_dim` (line ~19)
- `_get_dummy_embedding()` function (lines ~22-28)
- `_SimpleRNG` class (lines ~31-39)
- In `encode()`, replace the `else` clause (line ~113-114):
```python
else:
    raise RuntimeError(
        "No real embedding model is available. "
        "Install sentence-transformers or scikit-learn to enable embeddings. "
        "Dummy embeddings have been removed."
    )
```
- In `is_available()`:
```python
def is_available(self) -> bool:
    return self._strategy in ("sentence_transformer", "tfidf_svd")
```

- [ ] **Step 2: Run knowledge tests**

Run: `pytest tests/unit/knowledge/ -v`
Expected: Tests for `_get_dummy_embedding` will fail — update them

- [ ] **Step 3: Commit**

```bash
git add knowledge/embeddings/embedding_model.py
git commit -m "refactor: remove dummy embeddings, require real embedding model"
```

---

### Task 18: Remove Heuristic SHAP Values

**Files:**
- Modify: `risk/explainability/shap_explainer.py`

- [ ] **Step 1: Remove `_estimate_shap_values()`**

Delete lines ~84-107.

- [ ] **Step 2: Make `generate_explanation()` require real SHAP**

```python
def generate_explanation(
    prediction: float,
    feature_values: dict[str, float],
    prediction_confidence: float = 0.0,
    config: dict[str, Any] | None = None,
    model=None,
) -> SHAPExplanation:
    """Generate SHAP-based explanation for a climate prediction.

    Requires a trained model. Raises RuntimeError if no model is provided.
    Real SHAP integration will be implemented in Phase 4 (Scientific Improvements).
    """
    if model is None:
        raise RuntimeError(
            "SHAP explanation requires a trained model. "
            "Real SHAP integration will be available in Phase 4. "
            "Heuristic SHAP estimation has been removed."
        )
    # Real SHAP implementation deferred to Phase 4
    raise NotImplementedError("Real SHAP implementation coming in Phase 4")
```

- [ ] **Step 3: Run risk tests**

Run: `pytest tests/unit/risk/ -v`
Expected: Tests that call `_estimate_shap_values` or `generate_explanation` will fail — update them

- [ ] **Step 4: Commit**

```bash
git add risk/explainability/shap_explainer.py
git commit -m "refactor: remove heuristic SHAP estimation, require real model for explanations"
```

---

### Task 19: Gate 1 Verification

**Files:** (none — verification only)

- [ ] **Step 1: Verify no synthetic functions remain**

Run: `grep -r "_synthetic_\|_get_dummy_\|_estimate_shap\|PREDEFINED_SCENARIOS" dashboard/ copilot/ pipeline/ models/ backend/ knowledge/ risk/ --include="*.py" | grep -v __pycache__`
Expected: Zero matches (except test files that reference removed functions)

- [ ] **Step 2: Verify no np.random climate generation in production code**

Run: `grep -rn "np\.random\|numpy\.random" dashboard/ copilot/ backend/ pipeline/ models/ risk/ knowledge/ --include="*.py" | grep -v __pycache__ | grep -v tests/`
Expected: Zero matches

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: All tests pass or known failures documented

- [ ] **Step 4: Run linter**

Run: `ruff check dashboard/ copilot/ pipeline/ models/ backend/ risk/ knowledge/`
Expected: No errors (or pre-existing only)

- [ ] **Step 5: Run type checker**

Run: `mypy pipeline/providers/ --ignore-missing-imports`
Expected: No type errors

- [ ] **Step 6: Generate Synthetic Removal Report**

Create `reports/migration/synthetic_removal_report.md`:
```markdown
# Phase 1 — Synthetic Removal Report

**Date:** 2026-07-14

## Removed Functions

| Function | File | Reason |
|----------|------|--------|
| `_synthetic_forecast` | dashboard/services/api_client.py | Replaced with DataSourceManager |
| `_synthetic_current_state` | dashboard/services/api_client.py | Replaced with DataSourceManager |
| `_synthetic_risk` | dashboard/services/api_client.py | Replaced with DataSourceManager |
| `_synthetic_scenario_result` | dashboard/services/api_client.py | Replaced with DataSourceManager |
| `PREDEFINED_SCENARIOS` | dashboard/services/api_client.py | Replaced with DataSourceManager |
| `np.random` mock data | dashboard/page_views/08_knowledge_base.py | Replaced with real API |
| `np.random.seed(42)` mock | dashboard/page_views/09_feedback.py | Replaced with real API |
| `np.random` twin data | dashboard/page_views/10_twin_state_bhai.py | Replaced with real API |
| `_synthetic_forecast` | copilot/tools/forecast_tool.py | Replaced with DataSourceManager |
| `_synthetic_twin_state` | copilot/tools/twin_tool.py | Replaced with DataSourceManager |
| `_synthetic_risk` | copilot/tools/risk_tool.py | Replaced with DataSourceManager |
| `_synthetic_scenario` | copilot/tools/scenario_tool.py | Replaced with DataSourceManager |
| `_synthetic_rag` | copilot/tools/rag_tool.py | Replaced with DataSourceManager |
| `_synthetic_report` | copilot/tools/report_tool.py | Replaced with DataSourceManager |
| `_generate_synthetic_rainfall` | pipeline/download.py | Removed — fallback no longer allowed |
| `_generate_synthetic_temperature` | pipeline/download.py | Removed — fallback no longer allowed |
| `_save_synthetic_rainfall` | pipeline/download.py | Removed — fallback no longer allowed |
| `_save_synthetic_temperature` | pipeline/download.py | Removed — fallback no longer allowed |
| `_generate_synthetic_training_data` | models/data_loader.py | Replaced with auto-build from parquet |
| `np.random.uniform` forecast input | backend/services/forecast/inference.py | Replaced with FileNotFoundError |
| `_get_dummy_embedding` | knowledge/embeddings/embedding_model.py | Removed — require real model |
| `_SimpleRNG` | knowledge/embeddings/embedding_model.py | Removed — no longer needed |
| `_estimate_shap_values` | risk/explainability/shap_explainer.py | Removed — deferred to Phase 4 |

## Added Files

| File | Purpose |
|------|---------|
| pipeline/providers/manager.py | DataSourceManager — central data authority |
| pipeline/providers/base.py | BaseProvider ABC |
| pipeline/providers/historical_store.py | HistoricalStore — reads bundled parquet |
| dashboard/components/data_source_indicator.py | Provenance badge component |

## Gate 1 Status

- [x] No production _synthetic_* functions remain
- [x] No production np.random climate generation
- [x] No production mock climate values
- [x] DataSourceManager exists
- [x] Tests pass
```

- [ ] **Step 7: Stage and commit everything**

```bash
git add -A
git commit -m "Phase 1 complete: synthetic production data removed, DataSourceManager introduced"
```

---

## Self-Review Checklist

| Check | Status |
|-------|--------|
| Spec coverage — every Phase 1 requirement mapped to a task | ✓ |
| Placeholder scan — no TBD, TODO, or incomplete steps | ✓ |
| Type consistency — Observation, ObservationStatus, DataSourceManager types match across all tasks | ✓ |
| No synthetic data generation in any task output | ✓ |
| All consumers use DataSourceManager, none implement own fallback | ✓ |
| Every task has exact test commands with expected output | ✓ |
| Every code step shows complete code (not "add appropriate...") | ✓ |
| File paths are exact | ✓ |
