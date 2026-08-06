"""Historical context for hazard assessments.

Computes percentiles, climatology, and anomalies from REAL historical
data stored in ParquetObservationStore.  Caches computed climatology
per location to avoid recalculating 5+ years of history per request.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from risk.models.hazard import HistoricalContext

logger = logging.getLogger(__name__)

try:
    from simulator.repository.parquet_store import ParquetObservationStore
except ImportError:
    ParquetObservationStore = None


class HistoricalContextService:
    """Compute historical context for a location from REAL observation data."""

    def __init__(
        self,
        store: Any | None = None,
        climatology_period_days: int = 365,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        self._store = store
        self._climatology_period_days = climatology_period_days
        self._cache_ttl = cache_ttl_seconds
        self._climatology_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._cache_lock = threading.Lock()

    def _ensure_store(self) -> Any:
        if self._store is None and ParquetObservationStore is not None:
            self._store = ParquetObservationStore()
        return self._store

    def _get_all_values(
        self, location_id: str, variable: str, days: int | None = None
    ) -> list[float]:
        store = self._ensure_store()
        values: list[float] = []
        if store is not None:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=days or self._climatology_period_days)
            try:
                obs_list = store.query_observations(location_id, start, end)
                var_map = {
                    "temperature_2m": "temperature_2m",
                    "precipitation_mm": "precipitation_mm",
                    "max_temp": "temperature_2m",
                    "rainfall": "precipitation_mm",
                }
                attr = var_map.get(variable, variable)
                for o in obs_list:
                    v = getattr(o, attr, None)
                    if v is not None:
                        values.append(float(v))
            except Exception as exc:
                logger.debug("Historical query failed for %s: %s", location_id, exc)

        if len(values) >= 2:
            return values

        # Fallback: REAL Open-Meteo CSVs already in the pipeline.
        try:
            from risk.evaluation.feature_enrichment import load_real_observation_frame

            df = load_real_observation_frame()
            if df is not None and not df.empty:
                col = "Rainfall" if variable in {"precipitation_mm", "rainfall"} else "MaxTemp"
                if col in df.columns:
                    return [float(v) for v in df[col].dropna().tolist()]
        except Exception as exc:
            logger.debug("CSV climatology fallback failed: %s", exc)
        return values

    def compute_climatology(self, location_id: str, variable: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc).timestamp()
        with self._cache_lock:
            cached = self._climatology_cache.get(f"{location_id}:{variable}")
            if cached and (now - cached[0]) < self._cache_ttl:
                return dict(cached[1])

        values = self._get_all_values(location_id, variable)
        result: dict[str, Any] = {
            "reference_period_days": self._climatology_period_days,
            "count": len(values),
        }
        if values:
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            result["mean"] = sum(values) / n
            result["min"] = min(values)
            result["max"] = max(values)
            result["p50"] = sorted_vals[n // 2]
            result["p95"] = sorted_vals[int(n * 0.95)]
            result["p99"] = sorted_vals[int(n * 0.99)]
        else:
            result["mean"] = None
            result["p50"] = None
            result["p95"] = None
            result["p99"] = None

        with self._cache_lock:
            self._climatology_cache[f"{location_id}:{variable}"] = (now, result)
        return result

    def get_historical_context(
        self,
        location_id: str,
        variable: str,
        current_value: float,
        method: str = "HISTORICAL_PERCENTILE_V1",
    ) -> HistoricalContext | None:
        climo = self.compute_climatology(location_id, variable)
        if climo.get("count", 0) < 2:
            return None

        mean_val = climo["mean"]
        p50 = climo["p50"]
        p95 = climo["p95"]
        p99 = climo["p99"]
        anomaly = current_value - mean_val if mean_val is not None else None
        percentile = self._compute_percentile(current_value, location_id, variable)
        return HistoricalContext(
            reference_period=f"last_{self._climatology_period_days}_days",
            location_id=location_id,
            variable=variable,
            current_value=round(current_value, 2),
            percentile=round(percentile, 1) if percentile is not None else None,
            mean=round(mean_val, 2) if mean_val is not None else None,
            p50=round(p50, 2) if p50 is not None else None,
            p95=round(p95, 2) if p95 is not None else None,
            p99=round(p99, 2) if p99 is not None else None,
            anomaly=round(anomaly, 2) if anomaly is not None else None,
            anomaly_unit="°C" if "temp" in variable else "mm",
            method=method,
            dataset_id="parquet_observation_store",
        )

    def _compute_percentile(self, value: float, location_id: str, variable: str) -> float | None:
        values = self._get_all_values(location_id, variable)
        if not values:
            return None
        count_less = sum(1 for v in values if v < value)
        count_equal = sum(1 for v in values if v == value)
        return ((count_less + 0.5 * count_equal) / len(values)) * 100.0
