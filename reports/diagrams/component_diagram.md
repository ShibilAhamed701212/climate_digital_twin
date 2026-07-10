# Component Diagram

## Legend

Components are grouped by subsystem. Abstract base classes/interfaces are shown in *italics*. Inheritance is `--|>`, composition is `*--`, association is `-->`.

```mermaid
classDiagram

    %% ──────────────────────────────────────────
    %% FORECASTING SUBSYSTEM
    %% ──────────────────────────────────────────
    class PhysicsValidator {
        +rainfall_upper: float
        +temp_lower: float
        +temp_upper: float
        +target_names: list[str]
        +validate(predictions: Tensor) Tensor
        +validate_single(rainfall, max_temp, min_temp) tuple
    }

    class ModelRegistry {
        -_models: dict
        +register(name, arch, ckpt, metrics) dict
        +get(name) dict
        +list_models() list
        +get_best(metric, ascending) dict
        +update_metrics(name, metrics) dict
    }

    class DataLoader {
        +data_dir: str
        +sequence_length: int
        +batch_size: int
        +get_train_loader() DataLoader
        +get_val_loader() DataLoader
        +get_test_loader() DataLoader
    }

    class Trainer {
        +model: nn.Module
        +config: dict
        +train(train_loader, val_loader) History
        +early_stopping: bool
        +checkpoint(path): void
    }

    class Evaluator {
        +predictions: array
        +targets: array
        +compute_rmse() float
        +compute_mae() float
        +compute_r2() float
        +compute_smape() float
        +generate_plots(path): void
    }

    class Predictor {
        +model: nn.Module
        +physics: PhysicsValidator
        +predict(input) dict
        +load_model(path): void
        +export_torchscript(path): void
    }

    class BaselineModel {
        +hidden_layers: list[int]
        +forward(x) Tensor
    }

    class LSTMModel {
        +hidden_dim: int
        +num_layers: int
        +dropout: float
        +bidirectional: bool
        +forward(x) Tensor
    }

    class TransformerModel {
        +d_model: int
        +nhead: int
        +num_encoder_layers: int
        +forward(x) Tensor
    }

    class ITransformerModel {
        +d_model: int
        +nhead: int
        +time_proj: Linear
        +forward(x) Tensor
    }

    class PatchTSTModel {
        +patch_len: int
        +d_model: int
        +patch_embed: PatchEmbedding
        +forward(x) Tensor
    }

    class TimeMixerModel {
        +d_model: int
        +num_layers: int
        +blocks: ModuleList
        +forward(x) Tensor
    }

    class EnsembleMetaLearner {
        +alpha: float
        +fit_intercept: bool
        -_meta_models: dict
        -_scalers: dict
        +fit(base_preds, targets) dict
        +predict(base_preds) array
        +get_weights() dict
    }

    BaselineModel --|> nn.Module
    LSTMModel --|> nn.Module
    TransformerModel --|> nn.Module
    ITransformerModel --|> nn.Module
    PatchTSTModel --|> nn.Module
    TimeMixerModel --|> nn.Module
    Predictor --> PhysicsValidator
    Predictor --> ModelRegistry
    Predictor --> BaselineModel
    Predictor --> LSTMModel
    Predictor --> TransformerModel
    Trainer --> BaselineModel
    Trainer --> LSTMModel
    Trainer --> TransformerModel
    Evaluator --> Trainer

    %% ──────────────────────────────────────────
    %% DIGITAL TWIN SUBSYSTEM
    %% ──────────────────────────────────────────
    class ClimateEntity {
        +location_id: str
        +latitude: float
        +longitude: float
        +district: str
        +rainfall: float
        +max_temp: float
        +min_temp: float
        +timestamp: datetime
        +update_state(**kwargs) ClimateEntity
        +serialize() dict
    }

    class StateType {
        <<enumeration>>
        CURRENT
        HISTORICAL
        FORECAST
        SCENARIO
    }

    class Version {
        <<frozen>>
        +version_id: int
        +entity_id: str
        +state_type: StateType
        +timestamp: datetime
    }

    class StateManager {
        -_versions: dict
        -_current: dict
        +record(entity, state_type) Version
        +get_current(location_id) ClimateEntity
        +get_history(location_id) list
        +rollback(location_id, version_id) Version
    }

    class TwinEvent {
        <<frozen>>
        +event_id: str
        +event_type: str
        +location_id: str
        +timestamp: datetime
        +data: dict
    }

    class EventBus {
        -_subscribers: dict
        -_history: list
        +subscribe(event_type, handler): void
        +unsubscribe(event_type, handler): void
        +publish(event): void
        +get_history() list
    }

    class TwinRepository {
        <<abstract>>
        +save(location_id, entity): void
        +load(location_id) ClimateEntity
        +list_locations() list
        +delete(location_id): void
    }

    class ParquetRepository {
        +base_path: str
        +compression: str
        -_cache: dict
        +save(location_id, entity): void
        +load(location_id) ClimateEntity
        +list_locations() list
    }

    class TwinService {
        +state_manager: StateManager
        +repository: TwinRepository
        +event_bus: EventBus
        +ingest_observation(entity) dict
        +get_current_state(location_id) dict
        +apply_forecast(entity) dict
        +get_historical_state(location_id) list
    }

    class DigitalTwinEngine {
        +twin_service: TwinService
        +ingest_observation(entity) dict
        +get_current_state(location_id) dict
        +apply_forecast(entity) dict
        +get_historical_state(location_id) list
        +rehydrate(): void
    }

    class TwinAPI {
        <<abstract>>
        +get_current(location_id) dict
        +ingest(entity) dict
        +get_history(location_id) list
    }

    ParquetRepository --|> TwinRepository
    TwinService --> StateManager
    TwinService --> TwinRepository
    TwinService --> EventBus
    DigitalTwinEngine --> TwinService
    DigitalTwinEngine --|> TwinAPI

    %% ──────────────────────────────────────────
    %% SCENARIO SUBSYSTEM
    %% ──────────────────────────────────────────
    class ScenarioDefinition {
        <<frozen>>
        +scenario_id: str
        +name: str
        +description: str
        +scenario_type: str
        +parameters: dict
        +duration_days: int
    }

    class SimulationResult {
        <<frozen>>
        +location_id: str
        +baseline: dict
        +modified: dict
        +deltas: dict
        +success: bool
        +error_message: str
    }

    class ScenarioRun {
        <<frozen>>
        +scenario: ScenarioDefinition
        +results: list
        +status: str
        +execution_time_ms: float
    }

    class ScenarioValidator {
        +validate(scenario): ValidationResult
        +validate_parameters(type, params): void
    }

    class ScenarioBuilder {
        +create_scenario(name, type, params) ScenarioDefinition
        +get_preset(name) ScenarioDefinition
        +list_presets() list
    }

    class ScenarioEngine {
        +run_simulation(scenario, baseline) ScenarioRun
        -_apply_modifications(entity, type, params) dict
        -_compute_deltas(baseline, modified) dict
    }

    class ScenarioService {
        +twin_engine: DigitalTwinEngine
        +event_bus: EventBus
        +create_scenario(scenario): void
        +run_simulation(scenario_id) ScenarioRun
        +list_scenarios() list
        +delete_scenario(scenario_id): void
    }

    class OutputGenerator {
        +export_json(result, path): void
        +export_csv(result, path): void
        +export_markdown(result, path): void
    }

    class ReportGenerator {
        +generate_summary(scenario) dict
        +generate_markdown_report(scenario) str
    }

    ScenarioService --> DigitalTwinEngine
    ScenarioService --> EventBus
    ScenarioService --> ScenarioValidator
    ScenarioService --> ScenarioEngine
    ScenarioEngine --> ScenarioDefinition
    ScenarioEngine --> SimulationResult
    ScenarioEngine --> ScenarioRun
    OutputGenerator --> ScenarioRun
    ReportGenerator --> ScenarioRun

    %% ──────────────────────────────────────────
    %% RISK SUBSYSTEM
    %% ──────────────────────────────────────────
    class RiskCategory {
        <<enumeration>>
        VERY_LOW
        LOW
        MODERATE
        HIGH
        SEVERE
    }

    class HeatRiskScore {
        <<frozen>>
        +score: float
        +max_temp_contribution: float
        +consecutive_hot_days_contribution: float
        +seasonal_anomaly_contribution: float
        +category: RiskCategory
    }

    class FloodRiskScore {
        <<frozen>>
        +score: float
        +rainfall_intensity_contribution: float
        +multi_day_accumulation_contribution: float
        +forecast_uncertainty_contribution: float
        +category: RiskCategory
    }

    class DroughtRiskScore {
        <<frozen>>
        +score: float
        +rainfall_deficit_contribution: float
        +temperature_increase_contribution: float
        +dry_period_days_contribution: float
        +category: RiskCategory
    }

    class CompositeRiskScore {
        <<frozen>>
        +score: float
        +heat_score: float
        +flood_score: float
        +drought_score: float
        +category: RiskCategory
    }

    class SHAPExplanation {
        <<frozen>>
        +base_value: float
        +feature_attributions: list
        +global_importance: list
    }

    class ClimateInsight {
        <<frozen>>
        +risk_type: str
        +severity: str
        +description: str
        +implication: str
    }

    class RiskReport {
        <<frozen>>
        +location_id: str
        +heat_risk: HeatRiskScore
        +flood_risk: FloodRiskScore
        +drought_risk: DroughtRiskScore
        +composite_risk: CompositeRiskScore
        +shap_explanation: SHAPExplanation
        +insights: list
        +to_dict() dict
    }

    class HeatRiskScorer {
        +weights: dict
        +calculate(max_temp, hot_days, anomaly) HeatRiskScore
    }

    class FloodRiskScorer {
        +weights: dict
        +calculate(rainfall, accumulation, uncertainty) FloodRiskScore
    }

    class DroughtRiskScorer {
        +weights: dict
        +calculate(deficit, temp_anomaly, dry_days) DroughtRiskScore
    }

    class CompositeRiskScorer {
        +weights: dict
        +calculate(heat, flood, drought) CompositeRiskScore
    }

    class RiskEngine {
        -config: dict
        +assess_all(location_id, climate_data) RiskReport
        +assess_heat(data) HeatRiskScore
        +assess_flood(data) FloodRiskScore
        +assess_drought(data) DroughtRiskScore
        +generate_full_report(location_id) RiskReport
    }

    class SHAPExplainer {
        +generate_explanation(factors, score) SHAPExplanation
        +get_global_feature_importance() list
    }

    class InsightsEngine {
        +generate_insights(heat, flood, drought) list
    }

    class RiskReportGenerator {
        +generate_report(risk_report, path): void
        +generate_markdown(risk_report) str
    }

    class RiskAPI {
        <<abstract>>
        +calculate_risk(data) RiskReport
        +generate_explanation(data) SHAPExplanation
        +generate_report(data) str
        +export_results(data, format): void
    }

    RiskEngine --> HeatRiskScorer
    RiskEngine --> FloodRiskScorer
    RiskEngine --> DroughtRiskScorer
    RiskEngine --> CompositeRiskScorer
    RiskEngine --> SHAPExplainer
    RiskEngine --> InsightsEngine
    RiskEngine --> RiskReportGenerator
    RiskEngine --|> RiskAPI
    RiskReport --> HeatRiskScore
    RiskReport --> FloodRiskScore
    RiskReport --> DroughtRiskScore
    RiskReport --> CompositeRiskScore
    RiskReport --> SHAPExplanation
    RiskReport --> ClimateInsight

    %% ──────────────────────────────────────────
    %% RAG SUBSYSTEM
    %% ──────────────────────────────────────────
    class DocumentFormat {
        <<enumeration>>
        MD
        TXT
        CSV
        JSON
        PDF
    }

    class Document {
        <<frozen>>
        +doc_id: str
        +title: str
        +format: DocumentFormat
        +content: str
        +metadata: dict
        +source_path: str
    }

    class Chunk {
        <<frozen>>
        +chunk_id: str
        +doc_id: str
        +content: str
        +metadata: dict
        +chunk_index: int
    }

    class SearchResult {
        <<frozen>>
        +chunk: Chunk
        +score: float
        +metadata: dict
    }

    class BaseLoader {
        <<abstract>>
        +read_file(path) str
        +parse(content) Document
        +supported_format() DocumentFormat
    }

    class MDLoader {
        +parse(content) Document
    }

    class TXTLoader {
        +parse(content) Document
    }

    class CSVLoader {
        +parse(content) Document
    }

    class JSONLoader {
        +parse(content) Document
    }

    class LoaderFactory {
        +get_loader(extension) BaseLoader
    }

    class TextChunker {
        +chunk_size: int
        +chunk_overlap: int
        +chunk(document) list
    }

    class EmbeddingModel {
        +model_name: str
        +dimension: int
        +embed(texts) array
        +embed_query(text) array
    }

    class FAISSStore {
        +index_path: str
        +metadata_path: str
        +add(embeddings, metadatas): void
        +search(query, top_k) list
        +delete_document(doc_id): void
        +clear(): void
        +list_sources() list
    }

    class SemanticSearch {
        +store: FAISSStore
        +embedder: EmbeddingModel
        +search(query, top_k, threshold) list
        +retrieve_context(query, filters) RetrievalContext
    }

    class ContextBuilder {
        +build_llm_context(results) str
        +build_sectioned_context(results) dict
        +format_for_dashboard(results) dict
    }

    class IndexingPipeline {
        +loaders: LoaderFactory
        +chunker: TextChunker
        +embedder: EmbeddingModel
        +store: FAISSStore
        +index_document(path) IndexingResult
        +index_directory(path) list
    }

    class KnowledgeAPI {
        +store: FAISSStore
        +embedder: EmbeddingModel
        +index(path) IndexingResult
        +search(query, top_k) list
        +delete(doc_id): void
        +list_sources() list
        +rebuild(): void
    }

    MDLoader --|> BaseLoader
    TXTLoader --|> BaseLoader
    CSVLoader --|> BaseLoader
    JSONLoader --|> BaseLoader
    LoaderFactory --> MDLoader
    LoaderFactory --> TXTLoader
    LoaderFactory --> CSVLoader
    LoaderFactory --> JSONLoader
    TextChunker --> Document
    TextChunker --> Chunk
    EmbeddingModel --> Chunk
    FAISSStore --> Chunk
    FAISSStore --> SearchResult
    SemanticSearch --> FAISSStore
    SemanticSearch --> EmbeddingModel
    ContextBuilder --> SearchResult
    IndexingPipeline --> BaseLoader
    IndexingPipeline --> TextChunker
    IndexingPipeline --> EmbeddingModel
    IndexingPipeline --> FAISSStore
    KnowledgeAPI --> IndexingPipeline
    KnowledgeAPI --> SemanticSearch

    %% ──────────────────────────────────────────
    %% COPILOT SUBSYSTEM
    %% ──────────────────────────────────────────
    class IntentType {
        <<enumeration>>
        FORECAST
        TWIN_STATE
        SCENARIO
        RISK
        RAG
        REPORT
        GREETING
        UNKNOWN
    }

    class IntentResult {
        <<frozen>>
        +intent: IntentType
        +confidence: float
        +entities: dict
        +sub_intent: str
    }

    class Plan {
        <<frozen>>
        +intent: IntentType
        +steps: list
        +tools_required: list
    }

    class ToolResult {
        <<frozen>>
        +tool_name: str
        +success: bool
        +data: dict
        +execution_ms: float
        +error: str
    }

    class CopilotResponse {
        <<frozen>>
        +message: str
        +intent: IntentType
        +tool_results: list
        +execution_ms: float
    }

    class ConversationTurn {
        <<frozen>>
        +query: str
        +response: CopilotResponse
        +timestamp: datetime
    }

    class BaseTool {
        <<abstract>>
        +run(**kwargs) dict
        +validate(**kwargs): bool
        +describe() str
        +health_check(): bool
    }

    class ForecastTool {
        +run(location, horizon) dict
    }

    class TwinTool {
        +run(location) dict
    }

    class ScenarioTool {
        +run(location, scenario_type) dict
    }

    class RiskTool {
        +run(location, risk_type) dict
    }

    class RAGRetrieverTool {
        +run(query) dict
    }

    class ReportTool {
        +run(location, report_type) dict
    }

    class ToolRegistry {
        -_tools: dict
        +register(tool): void
        +get(name) BaseTool
        +list_enabled() list
        +health_check_all() dict
    }

    class IntentAgent {
        +classify(query) IntentResult
        -_extract_entities(query) dict
    }

    class PlanningAgent {
        +create_plan(intent) Plan
    }

    class Executor {
        +execute(plan, context) list
        +execute_step(step) ToolResult
    }

    class ResponseGenerator {
        +generate(intent, results) str
        +format_forecast(data) str
        +format_twin_state(data) str
        +format_scenario(data) str
        +format_risk(data) str
        +format_rag(data) str
        +format_report(data) str
    }

    class ConversationMemory {
        +window_size: int
        +expiry_minutes: int
        +add_turn(turn): void
        +get_recent(n) list
        +clear(conversation_id): void
    }

    class CopilotOrchestrator {
        +intent_agent: IntentAgent
        +planner: PlanningAgent
        +executor: Executor
        +generator: ResponseGenerator
        +memory: ConversationMemory
        +process(query) CopilotResponse
    }

    class CopilotAPI {
        +orchestrator: CopilotOrchestrator
        +ask(query) CopilotResponse
        +new_conversation(): void
        +get_history(conversation_id) list
        +health_check(): bool
    }

    class ConversationReport {
        +generate_summary(history) dict
        +generate_markdown(history) str
        +save_report(history, path): void
    }

    ForecastTool --|> BaseTool
    TwinTool --|> BaseTool
    ScenarioTool --|> BaseTool
    RiskTool --|> BaseTool
    RAGRetrieverTool --|> BaseTool
    ReportTool --|> BaseTool
    ToolRegistry --> BaseTool
    IntentAgent --> IntentResult
    PlanningAgent --> Plan
    Executor --> BaseTool
    Executor --> ToolResult
    ResponseGenerator --> ToolResult
    CopilotOrchestrator --> IntentAgent
    CopilotOrchestrator --> PlanningAgent
    CopilotOrchestrator --> Executor
    CopilotOrchestrator --> ResponseGenerator
    CopilotOrchestrator --> ConversationMemory
    CopilotOrchestrator --> ToolRegistry
    CopilotAPI --> CopilotOrchestrator
    ConversationReport --> ConversationTurn

    %% ──────────────────────────────────────────
    %% CROSS-CUTTING RELATIONSHIPS
    %% ──────────────────────────────────────────
    DigitalTwinEngine --> ClimateEntity
    ScenarioService --> DigitalTwinEngine
    RiskEngine --> DigitalTwinEngine
    CopilotOrchestrator --> ForecastTool
    CopilotOrchestrator --> TwinTool
    CopilotOrchestrator --> ScenarioTool
    CopilotOrchestrator --> RiskTool
    CopilotOrchestrator --> RAGRetrieverTool
    CopilotOrchestrator --> ReportTool
```

## Package Dependency Map

| Package | Depends On | External Dependencies |
|---------|-----------|----------------------|
| `models/` | `pipeline/` (data) | torch, numpy, scikit-learn |
| `simulator/` | — | pandas, numpy, pyyaml |
| `risk/` | `simulator/` (twin state) | numpy, pyyaml |
| `knowledge/` | — | faiss, sentence-transformers, numpy |
| `copilot/` | `simulator/`, `risk/`, `knowledge/`, `models/` | httpx, pyyaml |
| `dashboard/` | — | streamlit, plotly, folium |
| `backend/` | all services | fastapi, uvicorn |
| `pipeline/` | — | pandas, numpy, requests |
