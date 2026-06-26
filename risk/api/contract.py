"""Risk API contract — abstract interface for downstream consumption.

Defines the public API surface for the Climate Risk Engine. All methods
return structured data suitable for dashboard, REST endpoints, and
RAG ingestion.
"""

from abc import ABC, abstractmethod
from typing import Any

from risk.models.risk_models import (
    RiskReport,
)


class RiskAPI(ABC):
    """Abstract contract for the Climate Risk Engine API.

    Implementations must provide all methods for risk computation,
    explanation, reporting, and export.
    """

    @abstractmethod
    def calculate_risk(
        self,
        location_id: str,
        district: str,
        max_temp: float,
        min_temp: float,
        rainfall: float,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Compute all risk scores for a location.

        Returns a serialized dict suitable for API response.
        """

    @abstractmethod
    def calculate_heat_risk(
        self,
        max_temp: float,
        consecutive_hot_days: int = 0,
        seasonal_anomaly: float = 0.0,
    ) -> dict[str, Any]:
        """Compute heat risk score."""

    @abstractmethod
    def calculate_flood_risk(
        self,
        rainfall: float,
        multi_day_accumulation: float | None = None,
        forecast_uncertainty: float = 0.0,
    ) -> dict[str, Any]:
        """Compute flood risk score."""

    @abstractmethod
    def calculate_drought_risk(
        self,
        rainfall: float,
        historical_mean_rainfall: float = 100.0,
        max_temp: float = 30.0,
        historical_mean_temp: float = 28.0,
        dry_period_days: int = 0,
    ) -> dict[str, Any]:
        """Compute drought risk score."""

    @abstractmethod
    def generate_explanation(
        self,
        prediction: float,
        feature_values: dict[str, float],
        prediction_confidence: float = 0.0,
    ) -> dict[str, Any]:
        """Generate SHAP explanation for a prediction."""

    @abstractmethod
    def generate_report(
        self,
        location_id: str,
        district: str,
        report: RiskReport,
        formats: list[str] | None = None,
    ) -> dict[str, str]:
        """Generate and save risk report."""

    @abstractmethod
    def export_results(
        self,
        location_id: str,
        report: RiskReport,
        output_format: str = "json",
    ) -> str:
        """Export risk results as a string (JSON/Markdown)."""
