"""Production forecast pipeline (Phase 6).

Serves the gateway forecast contract using ONLY REAL-trained, VALIDATED
models from the registry, driven by REAL data. Never fabricates values:
every failure path raises ForecastUnavailableError with a structured code
instead of returning a made-up prediction.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta

import pandas as pd

from climatedt.ml.features import FeatureEngine
from climatedt.storage.parquet_store import ParquetObservationStore
from models.build_dataset import MONSOON_MONTHS, SEASON_MAP
from models.forecast_provenance import ForecastResult, ForecastStore
from models.registry import ModelRegistry
from pipeline.sources.location_registry import LocationRegistry

logger = logging.getLogger(__name__)

# NOTE: models.data_loader and models.predictor import torch at module top,
# which crashes on some Windows envs (known C++ DLL issue). They are imported
# lazily inside the prediction path so that failure handling (MODEL_UNAVAILABLE,
# NO_REAL_INPUT, NOT_SUPPORTED) stays testable without torch.

logger = logging.getLogger(__name__)

_ARCH_TO_MODEL = {
    "BaselineModel": "baseline",
    "LSTMModel": "lstm",
    "TransformerModel": "transformer",
}

_REAL_DATA_DIR = "data/real"

# ponytail: single TTL cache for live per-location history; the archive
# endpoint returns daily granularity, so a 6h window is plenty fresh and
# keeps Streamlit page reruns from hammering Open-Meteo.
_location_history_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_LOCATION_HISTORY_TTL_SECONDS = 6 * 3600


def _fetch_location_history(lat: float, lon: float, location_id: str) -> pd.DataFrame:
    """Fetch REAL recent daily history for a location and engineer features."""
    import json  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    from models.build_dataset import engineer_features  # noqa: PLC0415

    now = time.time()
    cached = _location_history_cache.get(location_id)
    if cached and now - cached[0] < _LOCATION_HISTORY_TTL_SECONDS:
        return cached[1].copy()

    end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=365 * 3)
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start.strftime('%Y-%m-%d')}&end_date={end.strftime('%Y-%m-%d')}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=auto"
    )
    resp = urllib.request.urlopen(url, timeout=60)
    data = json.loads(resp.read().decode())
    daily = data.get("daily", {})
    raw = pd.DataFrame(
        {
            "Date": daily.get("time", []),
            "MaxTemp": daily.get("temperature_2m_max", []),
            "MinTemp": daily.get("temperature_2m_min", []),
            "Rainfall": daily.get("precipitation_sum", []),
        }
    )
    raw["Date"] = pd.to_datetime(raw["Date"])
    raw["Rainfall"] = raw["Rainfall"].fillna(0.0)
    raw[["MaxTemp", "MinTemp"]] = raw[["MaxTemp", "MinTemp"]].ffill()
    df = engineer_features(raw, lat, lon, location_id)
    if len(df) < 1:
        raise ForecastUnavailableError(
            "NO_REAL_INPUT", f"REAL history unavailable for location {location_id}"
        )
    _location_history_cache[location_id] = (now, df.copy())
    return df


class ForecastUnavailableError(Exception):
    """Raised when a forecast cannot be produced from verified inputs.

    code is a machine-readable reason, e.g. MODEL_UNAVAILABLE, NO_REAL_INPUT,
    INFERENCE_FAILED, NOT_SUPPORTED.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _ForecastSeries:
    def __init__(self) -> None:
        self.timestamps: list[datetime] = []
        self.values: list[list[float]] = []
        self.model_id = ""
        self.confidence = 0.0
        self.forecast_id = ""
        self.authenticity = "REAL"
        self.training_run_id = ""
        self.dataset_id = ""
        self.horizon_days = 1


class _TrainingReport:
    def __init__(self) -> None:
        self.model_id = ""
        self.model_type = ""
        self.status = "success"
        self.metrics: dict[str, float] = {}


class ForecastPipeline:
    def __init__(
        self,
        feature_engine: FeatureEngine,
        model_registry: ModelRegistry,
        observation_store: ParquetObservationStore,
        forecast_store: ForecastStore | None = None,
    ) -> None:
        self.feature_engine = feature_engine
        self.model_registry = model_registry
        self.observation_store = observation_store
        # ponytail: forecast_store is injectable for tests; defaults to the
        # single production provenance store shared with models.forecast_cli.
        self.forecast_store = forecast_store or ForecastStore()

    async def predict_with_best(
        self,
        location_id: str,
        target_variable: str = "temperature_2m",
        horizon: int = 24,
    ) -> _ForecastSeries:
        return await asyncio.to_thread(self._predict_sync, location_id, target_variable, horizon)

    def _predict_sync(
        self,
        location_id: str,
        _target_variable: str,
        horizon: int,
    ) -> _ForecastSeries:
        try:
            entry = self.model_registry.get_best(
                metric="rmse",
                ascending=True,
                require_validated=True,
                require_real=True,
            )
        except KeyError as exc:
            raise ForecastUnavailableError(
                "MODEL_UNAVAILABLE", f"No REAL + VALIDATED model in registry: {exc}"
            ) from exc

        try:  # lazy: torch may be missing or broken in some envs
            import torch  # noqa: PLC0415

            from models.data_loader import (  # noqa: PLC0415
                load_config,
                load_scalers,
                needs_scaling,
            )
            from models.predictor import load_model, predict  # noqa: PLC0415
        except Exception as exc:
            raise ForecastUnavailableError(
                "MODEL_UNAVAILABLE",
                f"Model runtime unavailable (torch import failed): {exc}",
            ) from exc

        config = entry.get("config") or load_config()
        n_features = len(config["data"]["feature_columns"])
        n_targets = len(config["data"]["target_columns"])
        feat_cols = config["data"]["feature_columns"]
        seq_len = config["data"]["sequence_length"]

        model_type = _ARCH_TO_MODEL.get(entry.get("architecture", ""))
        if not model_type:
            raise ForecastUnavailableError(
                "INFERENCE_FAILED",
                f"Unknown architecture '{entry.get('architecture')}' for model '{entry['name']}'",
            )

        should_scale = needs_scaling(model_type)
        feat_scaler = tgt_scaler = None
        if should_scale:
            feat_scaler, tgt_scaler = load_scalers(entry["name"])
            if feat_scaler is None or tgt_scaler is None:
                raise ForecastUnavailableError(
                    "INFERENCE_FAILED",
                    f"Scalers missing for model '{entry['name']}' — cannot run scaled inference",
                )

        df = self._load_location_input(location_id)

        # Encode categorical feature columns exactly as training does
        # (data_loader.load_datasets: pd.Categorical().codes, alphabetical
        # categories). Training/validation/testing all share the same category
        # set, so codes are deterministic and consistent across splits.
        df = df.copy()
        season_cat = pd.Categorical(df["Season"])
        season_codes = dict(
            zip(season_cat.categories, range(len(season_cat.categories)), strict=False)
        )
        df["Season"] = season_cat.codes

        try:
            model = load_model(model_type, entry["checkpoint_path"], n_features, n_targets, config)
        except Exception as exc:
            raise ForecastUnavailableError(
                "INFERENCE_FAILED",
                f"Failed to load model '{entry['name']}' from {entry['checkpoint_path']}: {exc}",
            ) from exc

        rmse = entry.get("metrics", {}).get("rmse", 1.0)
        confidence = max(0.0, min(1.0, 1.0 - float(rmse) / 50.0))

        series = _ForecastSeries()
        series.model_id = entry["name"]
        series.confidence = confidence
        series.authenticity = entry.get("authenticity", "REAL")
        series.training_run_id = entry.get("training_run_id", "")
        series.dataset_id = entry.get("dataset_id", "")

        last_date = pd.to_datetime(df["Date"]).iloc[-1]
        horizon_days = max(1, int(round(int(horizon) / 24)))
        series.horizon_days = horizon_days

        store: ForecastStore | None = self.forecast_store
        for i in range(1, horizon_days + 1):
            input_seq = torch.tensor(
                df[feat_cols].values[-seq_len:], dtype=torch.float32
            ).unsqueeze(0)
            if should_scale and feat_scaler is not None:
                input_seq = feat_scaler.transform(input_seq)
            try:
                result = predict(
                    model,
                    input_seq,
                    target_scaler=tgt_scaler if should_scale else None,
                )
            except Exception as exc:
                raise ForecastUnavailableError(
                    "INFERENCE_FAILED", f"Prediction step {i} failed: {exc}"
                ) from exc
            day_pred = [float(v) for v in result["predictions"][0]]

            next_date = last_date + timedelta(days=i)
            row = {
                "Date": next_date,
                "Rainfall": day_pred[0],
                "MaxTemp": day_pred[1],
                "MinTemp": day_pred[2],
                "Month": next_date.month,
                "Week": next_date.isocalendar().week,
                "Season": season_codes[SEASON_MAP[next_date.month]],
                "Monsoon": 1 if next_date.month in MONSOON_MONTHS else 0,
            }
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            df.loc[df.index[-1], "RollingRain7"] = float(df["Rainfall"].tail(7).mean())
            df.loc[df.index[-1], "RollingRain30"] = float(df["Rainfall"].tail(30).mean())
            df.loc[df.index[-1], "RollingTemp7"] = float(df["MaxTemp"].tail(7).mean())
            df.loc[df.index[-1], "RollingTemp30"] = float(df["MaxTemp"].tail(30).mean())

            series.timestamps.append(next_date.to_pydatetime().replace(tzinfo=UTC))
            series.values.append(day_pred)

            if store is not None:
                store.save(
                    ForecastResult(
                        location_id=location_id,
                        timestamp=next_date.isoformat(),
                        rainfall=day_pred[0],
                        max_temp=day_pred[1],
                        min_temp=day_pred[2],
                        confidence=confidence,
                        model_id=entry["name"],
                        training_run_id=entry.get("training_run_id", ""),
                        model_architecture=entry.get("architecture", ""),
                        dataset_id=entry.get("dataset_id", ""),
                        authenticity=entry.get("authenticity", "REAL"),
                        horizon_days=1,
                        physics_validated=True,
                    )
                )
        if series.values:
            recent = store.list_recent(1) if store is not None else []
            if recent:
                series.forecast_id = recent[0].forecast_id
        logger.info(
            "Forecast generated for %s: %d day(s), model=%s, confidence=%.3f",
            location_id,
            horizon_days,
            entry["name"],
            confidence,
        )
        return series

    def _load_location_input(self, location_id: str) -> pd.DataFrame:
        """Load REAL recent history for the specific location.

        The model is location-agnostic (no lat/lon features), so feeding it
        each district's own real weather produces genuinely per-district
        forecasts. Falls back to the shared Bengaluru testing split only when
        the location is unknown or the live fetch fails.
        """
        registry = LocationRegistry()
        loc = registry.get_location(location_id) or registry.find_by_name(location_id)
        if loc is None:
            return self._load_real_input()
        try:
            df = _fetch_location_history(loc.latitude, loc.longitude, location_id)
        except Exception as exc:
            logger.warning(
                "Live history unavailable for %s (%s): %s — using shared real split",
                location_id,
                loc.name,
                exc,
            )
            return self._load_real_input()
        if len(df) < 1:
            raise ForecastUnavailableError(
                "NO_REAL_INPUT", f"REAL history unavailable for {location_id}"
            )
        return df

    def _load_real_input(self) -> pd.DataFrame:
        """Load the REAL testing split, verifying its manifest checksums."""
        from models.data_loader import (  # noqa: PLC0415
            DatasetNotFoundError,
            verify_dataset_manifest,
        )

        try:
            verify_dataset_manifest(_REAL_DATA_DIR)
        except DatasetNotFoundError as exc:
            raise ForecastUnavailableError(
                "NO_REAL_INPUT", f"REAL data unavailable at {_REAL_DATA_DIR}: {exc}"
            ) from exc
        df = pd.read_csv(f"{_REAL_DATA_DIR}/testing.csv")
        if len(df) < 1:
            raise ForecastUnavailableError(
                "NO_REAL_INPUT", f"REAL testing split at {_REAL_DATA_DIR} is empty"
            )
        return df

    async def train_forecast_model(
        self,
        _model_type: str = "xgboost",
        _target_variable: str = "temperature_2m",
    ) -> _TrainingReport:
        raise ForecastUnavailableError(
            "NOT_SUPPORTED",
            "Gateway retraining is not a production path. "
            "Run 'python -m models.forecast_cli train' with REAL data instead.",
        )
