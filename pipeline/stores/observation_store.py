from __future__ import annotations

import ast
import json as json_mod
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.providers.manager import Observation

_logger = logging.getLogger(__name__)


def _parse_dict_field(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw or (isinstance(raw, str) and raw.strip() in ("{}", "")):
        return {}
    if isinstance(raw, str):
        try:
            return json_mod.loads(raw)
        except (json_mod.JSONDecodeError, ValueError):
            pass
        try:
            result = ast.literal_eval(raw)
            if isinstance(result, dict):
                return result
        except (ValueError, SyntaxError):
            pass
    return {}


def _observation_to_dict(obs: Observation) -> dict[str, Any]:
    return {
        "observation_id": obs.data_source_identifier + "_" + obs.run_id,
        "data_source_identifier": obs.data_source_identifier,
        "run_id": obs.run_id,
        "provider": obs.provider,
        "source_dataset": obs.source_dataset,
        "authenticity": obs.authenticity,
        "observation_status": obs.status.value,
        "latitude": obs.latitude,
        "longitude": obs.longitude,
        "observation_timestamp": obs.observation_timestamp,
        "ingestion_timestamp": obs.retrieved_timestamp,
        "variable": obs.variable,
        "location_id": obs.location_id,
        "values": json_mod.dumps(obs.values),
        "units": json_mod.dumps(obs.units),
        "quality_flag": obs.quality_flag,
        "schema_version": obs.schema_version,
        "dataset_version": obs.dataset_version,
        "age_seconds": obs.age_seconds,
        "confidence": obs.confidence,
        "message": obs.message,
    }


def _row_to_observation(row: Any, variable_hint: str = "") -> Observation:
    return Observation(
        provider=str(row.get("provider", "")),
        source_dataset=str(row.get("source_dataset", "")),
        authenticity=str(row.get("authenticity", "REAL")),
        status=row.get("observation_status", ""),
        observation_timestamp=str(row.get("observation_timestamp", "")),
        retrieved_timestamp=str(row.get("ingestion_timestamp", "")),
        latitude=float(row.get("latitude", 0)),
        longitude=float(row.get("longitude", 0)),
        variable=str(row.get("variable", variable_hint)),
        location_id=str(row.get("location_id", "")),
        run_id=str(row.get("run_id", "")),
        data_source_identifier=str(row.get("data_source_identifier", row.get("provider", ""))),
        dataset_version=str(row.get("dataset_version", "")),
        quality_flag=str(row.get("quality_flag", "raw")),
        schema_version=str(row.get("schema_version", "1.0.0")),
        age_seconds=float(row.get("age_seconds", 0)),
        confidence=float(row.get("confidence", 0)),
        message=str(row.get("message", "")),
        values=_parse_dict_field(row.get("values", "{}")),
        units=_parse_dict_field(row.get("units", "{}")),
    )


class ObservationStore:
    def __init__(self, base_dir: str | Path = "data/real") -> None:
        self._base_dir = Path(base_dir)
        self._normalized_dir = self._base_dir / "normalized"
        self._normalized_dir.mkdir(parents=True, exist_ok=True)

    def save_batch(self, observations: list[Observation], run_id: str = "") -> int:
        if not observations:
            return 0
        rows = [_observation_to_dict(o) for o in observations]
        df = pd.DataFrame(rows)
        ts = run_id or datetime.now().strftime("%Y%m%dT%H%M%SZ")
        filepath = self._normalized_dir / f"observations_{ts}.parquet"
        df.to_parquet(filepath, index=False)
        _logger.info("Saved %d observations to %s", len(observations), filepath)
        return len(observations)

    def latest(
        self, variable: str = "", _lat: float = 0.0, _lon: float = 0.0
    ) -> Observation | None:
        files = sorted(self._normalized_dir.glob("observations_*.parquet"), reverse=True)
        if not files:
            return None
        df = pd.read_parquet(files[0])
        if variable and "variable" in df.columns:
            subset = df[df["variable"].str.contains(variable, na=False)]
            if not subset.empty:
                df = subset
        if df.empty:
            return None
        row = df.iloc[-1]
        return _row_to_observation(row, variable_hint=variable)

    def query(
        self,
        variable: str = "",
        _lat: float = 0.0,
        _lon: float = 0.0,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Observation]:
        files = sorted(self._normalized_dir.glob("observations_*.parquet"), reverse=True)
        if not files:
            return []
        dfs: list[pd.DataFrame] = []
        for f in files:
            dfs.append(pd.read_parquet(f))
        df = pd.concat(dfs, ignore_index=True)
        if variable and "variable" in df.columns:
            df = df[df["variable"].str.contains(variable, na=False)]
        if start and "observation_timestamp" in df.columns:
            df = df[df["observation_timestamp"] >= start.isoformat()]
        if end and "observation_timestamp" in df.columns:
            df = df[df["observation_timestamp"] <= end.isoformat()]
        results: list[Observation] = []
        for _, row in df.iterrows():
            results.append(_row_to_observation(row, variable_hint=variable))
        return results
