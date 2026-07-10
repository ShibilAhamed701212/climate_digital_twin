from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current server timestamp")
    services: dict[str, str] = Field(default_factory=dict, description="Per-service health status")


class ReadinessResponse(BaseModel):
    ready: bool = Field(..., description="Whether the system is ready")
    services: dict[str, bool] = Field(default_factory=dict, description="Per-service readiness")


class RiskAssessRequest(BaseModel):
    location_id: str = Field(..., description="Geographic location identifier")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude")
    include_explainability: bool = Field(True, description="Include explainability metadata")


class RiskAssessResponse(BaseModel):
    assessment_id: str = Field(..., description="Unique assessment identifier")
    location_id: str = Field(..., description="Geographic location identifier")
    composite_score: float = Field(..., ge=0.0, le=1.0, description="Composite risk score")
    composite_category: str = Field(..., description="Risk category label")
    scores: list[dict[str, Any]] = Field(..., description="Per-hazard risk scores")
    timestamp: str = Field(..., description="Assessment timestamp")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")


class BatchRiskAssessRequest(BaseModel):
    locations: list[dict[str, Any]] = Field(
        ...,
        description=("List of location objects, each with location_id, latitude, longitude"),
        min_length=1,
    )


class BatchRiskAssessResponse(BaseModel):
    assessments: dict[str, RiskAssessResponse] = Field(
        ..., description="Map of location_id to risk assessment"
    )
    total_locations: int = Field(..., description="Number of locations assessed")


class RiskTrendRequest(BaseModel):
    days: int = Field(90, ge=1, le=365, description="Number of days to analyse")


class RiskTrendResponse(BaseModel):
    location_id: str = Field(..., description="Geographic location identifier")
    assessments: list[RiskAssessResponse] = Field(..., description="Chronological risk assessments")
    days_analysed: int = Field(..., description="Number of days analysed")


class RiskExplainRequest(BaseModel):
    assessment_id: str = Field(..., description="Assessment to explain")
    location_id: str | None = Field(None, description="Location ID for the assessment")
    latitude: float = Field(default=0.0, ge=-90.0, le=90.0)
    longitude: float = Field(default=0.0, ge=-180.0, le=180.0)
    hazard_type: str | None = Field(None, description="Specific hazard type to explain")


class RiskExplainResponse(BaseModel):
    assessment_id: str = Field(..., description="Assessment identifier")
    hazard_contributions: dict[str, dict[str, float]] = Field(
        ..., description="Feature contributions per hazard type"
    )
    top_factors: list[str] = Field(..., description="Top contributing factors")


class CreateScenarioRequest(BaseModel):
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(..., description="Detailed description")
    scenario_type: str = Field(..., description="Scenario type identifier")
    location_id: str = Field(..., description="Target location")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    duration_days: int = Field(..., gt=0, description="Duration in days")
    temperature_delta: float | None = Field(None, description="Temperature change in °C")
    rainfall_multiplier: float | None = Field(None, description="Rainfall multiplier")
    humidity_delta: float | None = Field(None, description="Humidity change in %")
    wind_speed_delta: float | None = Field(None, description="Wind speed change in m/s")
    pressure_delta: float | None = Field(None, description="Pressure change in hPa")
    parameters: dict[str, float] = Field(default_factory=dict, description="Additional parameters")


class CreateScenarioResponse(BaseModel):
    scenario_id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Scenario name")
    created_at: str = Field(..., description="Creation timestamp")


class RunScenarioRequest(BaseModel):
    scenario_id: str = Field(..., description="Scenario to simulate")


class RunScenarioResponse(BaseModel):
    result_id: str = Field(..., description="Simulation result identifier")
    scenario_id: str = Field(..., description="Scenario identifier")
    location_id: str = Field(..., description="Location identifier")
    summary_statistics: dict[str, dict[str, float]] = Field(
        ..., description="Summary statistics per variable"
    )
    time_steps: list[str] = Field(..., description="Timestamps")
    execution_time_ms: float | None = Field(None, description="Execution time")


class CompareScenariosRequest(BaseModel):
    scenario_ids: list[str] = Field(..., min_length=2, description="Scenarios to compare")


class CompareScenariosResponse(BaseModel):
    comparisons: list[dict[str, Any]] = Field(..., description="Comparison results")
    total_comparisons: int = Field(..., description="Number of comparisons made")


class MonteCarloRequest(BaseModel):
    scenario_id: str = Field(..., description="Base scenario ID")
    distributions: dict[str, dict[str, float]] = Field(..., description="Parameter distributions")


class ScenarioDetailResponse(BaseModel):
    scenario_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Scenario name")
    description: str = Field(..., description="Detailed description")
    scenario_type: str = Field(..., description="Scenario type")
    location_id: str = Field(..., description="Target location")
    duration_days: int = Field(..., description="Duration in days")
    parameters: dict[str, float] = Field(..., description="Scenario parameters")


class GenerateFromTemplateRequest(BaseModel):
    location_id: str = Field(..., description="Target location")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    duration_days: int | None = Field(None, description="Duration override")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Template parameters")


class MonteCarloSimRequest(BaseModel):
    scenario_type: str = Field(..., description="Scenario type (temperature, rainfall, etc)")
    base_params: dict[str, Any] = Field(default_factory=dict, description="Baseline parameters")
    num_simulations: int = Field(
        1000, ge=1, le=100000, description="Number of Monte Carlo simulations"
    )
    confidence_level: float = Field(
        0.95, ge=0.5, le=0.999, description="Confidence level for intervals"
    )
    distributions: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "temperature_delta": {"distribution": "normal", "mean": 0.0, "std": 0.5}
        },
        description="Parameter distributions for sampling",
    )


class ScenarioConfig(BaseModel):
    name: str = Field(..., description="Scenario name")
    scenario_type: str = Field(..., description="Scenario type")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Scenario parameters")
    location_id: str = Field("unknown", description="Location identifier")


class CompareScenariosNewRequest(BaseModel):
    scenarios: list[ScenarioConfig] = Field(..., min_length=2, description="Scenarios to compare")
    baseline_index: int = Field(0, ge=0, description="Index of the baseline scenario in the list")


class EnsembleMemberConfig(BaseModel):
    config: ScenarioConfig
    weight: float = Field(1.0, ge=0.0, description="Ensemble member weight")


class EnsembleSimRequest(BaseModel):
    members: list[EnsembleMemberConfig] = Field(..., min_length=1, description="Ensemble members")
    location_id: str = Field("unknown", description="Target location identifier")


class ScenarioGeneratorRequest(BaseModel):
    scenario_type: str = Field(..., description="Scenario type to generate")
    location_id: str = Field(..., description="Target location")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    duration_days: int = Field(30, gt=0, description="Duration in days")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Additional generation parameters"
    )


class RAGAskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language question")
    k: int = Field(5, ge=1, le=50, description="Number of results to return")
    collection_id: str | None = Field(None, description="Restrict to collection")


class RAGAskResponse(BaseModel):
    query: str = Field(..., description="Original query")
    results: list[dict[str, Any]] = Field(..., description="Search results ranked by relevance")
    total_results: int = Field(..., description="Number of results")


class RAGIngestRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Document title")
    source: str = Field(..., description="Source attribution")
    content: str = Field(..., min_length=1, description="Document text content")
    content_type: str = Field("text/plain", description="MIME type")
    tags: list[str] = Field(default_factory=list, description="Tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RAGIngestResponse(BaseModel):
    document_id: str = Field(..., description="Document identifier")
    chunks_created: int = Field(..., description="Number of chunks created")
    title: str = Field(..., description="Document title")


class BatchIngestRequest(BaseModel):
    documents: list[RAGIngestRequest] = Field(..., min_length=1, description="Documents to ingest")


class BatchIngestResponse(BaseModel):
    results: dict[str, RAGIngestResponse] = Field(..., description="Per-document ingestion results")
    total_documents: int = Field(..., description="Documents ingested")
    total_chunks: int = Field(..., description="Total chunks created")


class RAGContextRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query string")
    max_tokens: int = Field(2000, ge=100, le=10000, description="Max context tokens")


class RAGContextResponse(BaseModel):
    query: str = Field(..., description="Original query")
    context: str = Field(..., description="Formatted context string")
    sources: int = Field(..., description="Number of sources included")


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Collection name")
    description: str = Field("", description="Collection description")


class CollectionStatsResponse(BaseModel):
    collection_id: str = Field(..., description="Collection identifier")
    name: str = Field(..., description="Collection name")
    document_count: int = Field(..., description="Number of documents")
    chunk_count: int = Field(..., description="Number of chunks")


class SearchCollectionRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    k: int = Field(5, ge=1, le=50, description="Results to return")


class SubmitRiskFeedbackRequest(BaseModel):
    assessment_id: str = Field(..., description="Risk assessment ID")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    corrected_score: float | None = Field(None, ge=0.0, le=1.0, description="Corrected risk score")
    comment: str | None = Field(None, description="User comment")


class SubmitForecastFeedbackRequest(BaseModel):
    forecast_id: str = Field(..., description="Forecast ID")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    observed_values: dict[str, float] | None = Field(None, description="Observed values")
    comment: str | None = Field(None, description="User comment")


class SubmitGeneralFeedbackRequest(BaseModel):
    location_id: str = Field(..., description="Location identifier")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    feedback_type: str = Field(
        ..., pattern="^(risk|forecast|general)$", description="Feedback type"
    )
    comment: str | None = Field(None, description="User comment")


class FeedbackResponse(BaseModel):
    record_id: str = Field(..., description="Feedback record identifier")
    status: str = Field(..., description="Feedback status")
    message: str = Field(..., description="Status message")


class FeedbackStatsResponse(BaseModel):
    total_feedback: int = Field(..., description="Total feedback count")
    avg_rating: float = Field(..., description="Average rating")
    rating_std: float = Field(..., description="Rating standard deviation")
    rating_distribution: dict[str, float] = Field(..., description="Rating distribution")
    feedback_types: dict[str, int] = Field(..., description="Feedback type counts")


class FeedbackTrendResponse(BaseModel):
    overall_trend: float = Field(..., description="Trend slope")
    first_period_avg: float = Field(..., description="First half average")
    second_period_avg: float = Field(..., description="Second half average")
    trend_direction: str = Field(..., description="Trend direction")
    improvement_pct: float = Field(..., description="Improvement percentage")


class LocationFeedbackResponse(BaseModel):
    location_id: str = Field(..., description="Location identifier")
    total_feedback: int = Field(..., description="Total feedback count")
    avg_rating: float = Field(..., description="Average rating")
    trend: str = Field(..., description="Rating trend")
    recent_avg: float | None = Field(None, description="Recent 30-day average")


class TwinStateResponse(BaseModel):
    entity_id: str = Field(..., description="Entity identifier")
    timestamp: str = Field(..., description="State timestamp")
    temperature_2m: float = Field(..., description="Temperature in °C")
    precipitation_mm: float = Field(..., description="Precipitation in mm")
    humidity_pct: float = Field(..., description="Humidity in %")
    pressure_hpa: float = Field(..., description="Pressure in hPa")
    wind_speed_10m: float = Field(..., description="Wind speed in m/s")
    data_source: str = Field(..., description="Data source")
    quality_flag: str = Field(..., description="Quality flag")


class UpdateTwinStateRequest(BaseModel):
    entity_id: str = Field(..., description="Entity identifier")
    delta_temperature: float = Field(0.0, description="Temperature delta in °C")
    delta_precipitation: float = Field(0.0, description="Precipitation delta in mm")
    delta_humidity: float = Field(0.0, description="Humidity delta in %")
    delta_pressure: float = Field(0.0, description="Pressure delta in hPa")
    delta_wind_speed: float = Field(0.0, description="Wind speed delta in m/s")
    source: str = Field("api", description="Update source identifier")


class UpdateTwinStateResponse(BaseModel):
    version_id: str = Field(..., description="New version identifier")
    version_number: int = Field(..., description="New version number")
    entity_id: str = Field(..., description="Entity identifier")


class TwinEntityResponse(BaseModel):
    entity_id: str = Field(..., description="Entity identifier")
    name: str = Field(..., description="Entity name")
    location_id: str = Field(..., description="Location identifier")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")


class TwinHistoryResponse(BaseModel):
    entity_id: str = Field(..., description="Entity identifier")
    versions: list[dict[str, Any]] = Field(..., description="Version history entries")
    total_versions: int = Field(..., description="Total version count")


class RollbackRequest(BaseModel):
    entity_id: str = Field(..., description="Entity identifier")
    version_number: int = Field(..., gt=0, description="Target version number")


class RollbackResponse(BaseModel):
    entity_id: str = Field(..., description="Entity identifier")
    rolled_back_to_version: int = Field(..., description="Version rolled back to")
    new_version_number: int = Field(..., description="New version after rollback")


class ForecastPredictRequest(BaseModel):
    location_id: str = Field(..., description="Location to forecast")
    target_variable: str = Field("temperature_2m", description="Variable to forecast")
    horizon_hours: int = Field(72, ge=1, le=720, description="Forecast horizon")
    model_id: str | None = Field(None, description="Specific model to use")


class ForecastPredictResponse(BaseModel):
    location_id: str = Field(..., description="Location identifier")
    target_variable: str = Field(..., description="Forecast variable")
    timestamps: list[str] = Field(..., description="Forecast timestamps")
    values: list[float] = Field(..., description="Forecast values")
    model_id: str = Field(..., description="Model used")
    created_at: str = Field(..., description="Generation timestamp")


class ForecastModelsResponse(BaseModel):
    models: list[dict[str, Any]] = Field(..., description="Available models")
    total: int = Field(..., description="Total model count")


class ForecastPerformanceResponse(BaseModel):
    model_id: str = Field(..., description="Model identifier")
    metrics: dict[str, float] = Field(..., description="Performance metrics")
    target_variable: str = Field(..., description="Target variable")


class RetrainResponse(BaseModel):
    model_id: str = Field(..., description="New model identifier")
    model_type: str = Field(..., description="Model type")
    target_variable: str = Field(..., description="Target variable")
    status: str = Field(..., description="Training status")
    metrics: dict[str, float] = Field(default_factory=dict, description="Training metrics")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error description")
    error_code: str | None = Field(None, description="Machine-readable error code")
    timestamp: str = Field(..., description="Error timestamp")


class ValidationErrorResponse(BaseModel):
    detail: list[dict[str, Any]] = Field(..., description="Validation error details")
