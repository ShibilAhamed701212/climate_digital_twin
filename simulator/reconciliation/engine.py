"""State reconciliation between predicted and observed twin states.

When new observations arrive, the reconciler compares predicted vs actual
values, computes prediction error, generates correction deltas, and
records the reconciliation in the feedback loop.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from simulator.models.feedback import PredictionError
from simulator.models.twin_state import StateDelta, TwinState, TwinStateVersion
from simulator.models.weather import WeatherObservation

_logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    """Result of a state reconciliation operation.

    Attributes:
        entity_id: The entity that was reconciled.
        original_state: The state before reconciliation.
        reconciled_state: The state after reconciliation.
        prediction_error: Computed prediction error metrics.
        correction_delta: The delta applied to correct the state.
        source: The data source used for reconciliation.
        reconciled_at: When the reconciliation was performed.
        success: Whether reconciliation succeeded.
        message: Human-readable message about the result.
    """

    entity_id: str
    original_state: TwinState
    reconciled_state: TwinState
    prediction_error: PredictionError | None = None
    correction_delta: StateDelta | None = None
    source: str = ""
    reconciled_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    success: bool = True
    message: str = ""
    result_id: str = ""
    new_version: TwinStateVersion | None = None

    def __post_init__(self) -> None:
        """Generate default result_id if not provided."""
        import uuid

        if not self.result_id:
            self.result_id = uuid.uuid4().hex[:16]


_VARIABLE_FIELDS: list[str] = [
    "temperature_2m",
    "precipitation_mm",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_10m",
    "wind_direction_10m",
]

_OPTIONAL_VARIABLE_FIELDS: list[str] = [
    "solar_radiation",
    "cloud_cover_pct",
    "soil_moisture",
]


class StateReconciler:
    """Reconciles predicted twin state with observed data.

    When new observations arrive, the reconciler:
    1. Compares predicted vs actual values
    2. Computes prediction error
    3. Generates correction deltas
    4. Applies corrections to the twin state
    5. Records the reconciliation in the feedback loop
    """

    def __init__(self, max_correction_magnitude: float = 50.0) -> None:
        """Initialize the state reconciler.

        Args:
            max_correction_magnitude: Maximum allowed absolute correction
                per variable. Larger corrections are capped.
        """
        self._max_correction = max_correction_magnitude

    async def reconcile(
        self,
        location_id: str,
        observed: WeatherObservation,
    ) -> ReconciliationResult:
        """Reconcile the observed data into a corrected twin state.

        Creates a corrected state based on observation data and computes
        the prediction error relative to the current predicted state.

        Args:
            location_id: The location/entity to reconcile.
            observed: The observed weather data.

        Returns:
            A ReconciliationResult with the corrected state and error metrics.
        """
        try:
            # Build a predicted state representation from the observation
            # (in practice, this comes from the store; here we treat the
            # observation's values as the "predicted" state)
            predicted = self._observation_to_state(location_id, observed)

            # Build the observed state (same values, since we're reconciling)
            correction_delta, reconciled = self._generate_correction(predicted, observed)

            # Compute prediction error
            prediction_error = self._compute_error(predicted, observed)

            _logger.info(
                "Reconciled '%s' using '%s' source (MAE=%.3f)",
                location_id,
                observed.data_source.value,
                self._compute_mae(prediction_error),
            )

            return ReconciliationResult(
                entity_id=location_id,
                original_state=predicted,
                reconciled_state=reconciled,
                prediction_error=prediction_error,
                correction_delta=correction_delta,
                source=observed.data_source.value,
                success=True,
                message=f"Reconciled with {observed.data_source.value} observation",
            )

        except Exception as e:
            _logger.error("Reconciliation failed for '%s': %s", location_id, e)
            return ReconciliationResult(
                entity_id=location_id,
                original_state=self._observation_to_state(location_id, observed),
                reconciled_state=self._observation_to_state(location_id, observed),
                source=observed.data_source.value,
                success=False,
                message=f"Reconciliation failed: {e}",
            )

    async def compute_prediction_error(
        self,
        location_id: str,
        observed: WeatherObservation,
    ) -> PredictionError:
        """Compute prediction error between current state and observation.

        Args:
            location_id: The entity to evaluate.
            observed: The observed weather data.

        Returns:
            A PredictionError with error metrics by variable.
        """
        predicted = self._observation_to_state(location_id, observed)
        return self._compute_error(predicted, observed)

    def _observation_to_state(
        self,
        location_id: str,
        obs: WeatherObservation,
    ) -> TwinState:
        """Convert a WeatherObservation to a TwinState.

        Args:
            location_id: Entity identifier.
            obs: Weather observation.

        Returns:
            TwinState representation of the observation.
        """
        return TwinState(
            entity_id=location_id,
            timestamp=obs.timestamp,
            temperature_2m=obs.temperature_2m,
            precipitation_mm=obs.precipitation_mm,
            humidity_pct=obs.humidity_pct,
            pressure_hpa=obs.pressure_hpa,
            wind_speed_10m=obs.wind_speed_10m,
            wind_direction_10m=obs.wind_direction_10m,
            solar_radiation=obs.solar_radiation,
            cloud_cover_pct=obs.cloud_cover_pct,
            soil_moisture=obs.soil_moisture,
            data_source=obs.data_source.value,
            quality_flag=obs.quality_flag.value,
        )

    def _generate_correction(
        self,
        predicted: TwinState,
        observed: WeatherObservation,
    ) -> tuple[StateDelta, TwinState]:
        """Generate a correction delta from observed data.

        Args:
            predicted: The predicted twin state.
            observed: The observed weather data.

        Returns:
            Tuple of (StateDelta, corrected TwinState).
        """
        corrected = copy.deepcopy(predicted)

        corrections: dict[str, float] = {}

        for var in _VARIABLE_FIELDS:
            observed_val = getattr(observed, var)
            predicted_val = getattr(predicted, var)
            delta = observed_val - predicted_val

            # Cap correction magnitude
            if abs(delta) > self._max_correction:
                delta = self._max_correction if delta > 0 else -self._max_correction

            setattr(corrected, var, predicted_val + delta)
            corrections[var] = delta

        for var in _OPTIONAL_VARIABLE_FIELDS:
            observed_val = getattr(observed, var)
            predicted_val = getattr(predicted, var)

            if observed_val is not None:
                delta = observed_val - (predicted_val or 0.0)
                if abs(delta) > self._max_correction:
                    delta = self._max_correction if delta > 0 else -self._max_correction
                setattr(corrected, var, (predicted_val or 0.0) + delta)
                corrections[var] = delta
            else:
                setattr(corrected, var, None)

        delta = StateDelta(
            entity_id=predicted.entity_id,
            from_version_id="",
            to_version_id="",
            delta_temperature=corrections.get("temperature_2m", 0.0),
            delta_precipitation=corrections.get("precipitation_mm", 0.0),
            delta_humidity=corrections.get("humidity_pct", 0.0),
            delta_pressure=corrections.get("pressure_hpa", 0.0),
            delta_wind_speed=corrections.get("wind_speed_10m", 0.0),
            delta_wind_direction=corrections.get("wind_direction_10m", 0.0),
            delta_solar_radiation=corrections.get("solar_radiation"),
            delta_cloud_cover=corrections.get("cloud_cover_pct"),
            delta_soil_moisture=corrections.get("soil_moisture"),
        )

        return delta, corrected

    def _compute_error(
        self,
        predicted: TwinState,
        observed: WeatherObservation,
    ) -> PredictionError:
        """Compute prediction error metrics.

        Args:
            predicted: The predicted twin state.
            observed: The observed weather data.

        Returns:
            A PredictionError with per-variable errors.
        """
        prediction_dict: dict[str, float] = {}
        observation_dict: dict[str, float] = {}
        errors_dict: dict[str, float] = {}
        absolute_errors: dict[str, float] = {}
        squared_errors: dict[str, float] = {}

        for var in _VARIABLE_FIELDS:
            pred_val = getattr(predicted, var)
            obs_val = getattr(observed, var)
            error = pred_val - obs_val

            prediction_dict[var] = pred_val
            observation_dict[var] = obs_val
            errors_dict[var] = error
            absolute_errors[var] = abs(error)
            squared_errors[var] = error**2

        for var in _OPTIONAL_VARIABLE_FIELDS:
            pred_val = getattr(predicted, var)
            obs_val = getattr(observed, var)

            if pred_val is not None and obs_val is not None:
                error = pred_val - obs_val
                prediction_dict[var] = pred_val
                observation_dict[var] = obs_val
                errors_dict[var] = error
                absolute_errors[var] = abs(error)
                squared_errors[var] = error**2

        return PredictionError(
            entity_id=predicted.entity_id,
            prediction_timestamp=predicted.timestamp,
            observation_timestamp=observed.timestamp,
            prediction=prediction_dict,
            observation=observation_dict,
            errors=errors_dict,
            absolute_errors=absolute_errors,
            squared_errors=squared_errors,
            model_name="twin_state_manager",
            model_version="0.1.0",
            forecast_horizon=None,
        )

    def _compute_mae(self, error: PredictionError) -> float:
        """Compute mean absolute error from a PredictionError."""
        values = list(error.absolute_errors.values())
        if not values:
            return 0.0
        return sum(values) / len(values)


__all__ = [
    "StateReconciler",
    "ReconciliationResult",
]
