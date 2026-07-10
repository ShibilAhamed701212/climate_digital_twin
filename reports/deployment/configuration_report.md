# Configuration Report — Climate Digital Twin

## Overview

The system externalizes all configuration to 7 YAML files, covering data pipeline, ML models, digital twin, scenarios, risk assessment, RAG knowledge base, and Copilot agent.

---

## 1. `config/data_config.yaml` — Data Pipeline Configuration

**Purpose:** Defines project scope, data sources, feature engineering parameters, and dataset splits.

| Parameter | Value | Description |
|---|---|---|
| `project.name` | `climate-digital-twin` | Project identifier |
| `project.region` | `Karnataka` | Pilot region |
| `project.pilot_districts` | `[Bengaluru Urban, Mysuru, Belagavi, Dakshina Kannada, Kalaburagi]` | 5 pilot districts |
| `data.raw_dir` | `data/raw` | Raw data directory |
| `data.interim_dir` | `data/interim` | Interim data directory |
| `data.processed_dir` | `data/processed` | Processed data directory |
| `data.external_dir` | `data/external` | External data directory |
| `sources.primary` | `nasa_power` | Primary data source |
| `sources.nasa_power.endpoint` | `https://power.larc.nasa.gov/api/temporal/daily/point` | NASA POWER API endpoint |
| `sources.nasa_power.parameters.rainfall` | `PRECTOTCORR` | NASA POWER parameter for rainfall |
| `sources.nasa_power.parameters.max_temp` | `T2M_MAX` | NASA POWER parameter for max temperature |
| `sources.nasa_power.parameters.min_temp` | `T2M_MIN` | NASA POWER parameter for min temperature |
| `sources.nasa_power.max_workers` | `4` | Parallel download workers |
| `datasets.rainfall.filename` | `rainfall.parquet` | Rainfall dataset filename |
| `datasets.max_temp.filename` | `maxtemp.parquet` | Max temp dataset filename |
| `datasets.min_temp.filename` | `mintemp.parquet` | Min temp dataset filename |
| `date_range.start` | `1981-01-01` | Data collection start date |
| `date_range.end` | `2023-12-31` | Data collection end date |
| `karnataka_bounds.min_lat` | `11.5` | Karnataka minimum latitude |
| `karnataka_bounds.max_lat` | `18.5` | Karnataka maximum latitude |
| `karnataka_bounds.min_lon` | `74.0` | Karnataka minimum longitude |
| `karnataka_bounds.max_lon` | `78.5` | Karnataka maximum longitude |
| `pipeline.train_split` | `0.70` | Training split ratio (chronological) |
| `pipeline.val_split` | `0.15` | Validation split ratio |
| `pipeline.test_split` | `0.15` | Test split ratio |
| `pipeline.sequence_length` | `30` | Sequence window length (days) |
| `pipeline.batch_size` | `64` | Training batch size |
| `pipeline.random_seed` | `42` | Random seed for reproducibility |

---

## 2. `models/configs/model_config.yaml` — ML Model Configuration

**Purpose:** Controls data loading, model architectures (Baseline/LSTM/Transformer), training, evaluation, and export.

| Parameter | Default | Description |
|---|---|---|
| `data.sequence_length` | `30` | Input sequence length (days) |
| `data.batch_size` | `64` | Batch size for DataLoader |
| `data.feature_columns` | `[Rainfall, MaxTemp, MinTemp, Month, Week, Season, Monsoon, RollingRain7, RollingRain30, RollingTemp7, RollingTemp30]` | 11 input features |
| `data.target_columns` | `[Rainfall, MaxTemp, MinTemp]` | 3 prediction targets |
| `baseline.hidden_layers` | `[64, 32]` | MLP hidden layer sizes |
| `baseline.learning_rate` | `0.001` | MLP learning rate |
| `baseline.epochs` | `50` | MLP training epochs |
| `lstm.hidden_dim` | `128` | LSTM hidden dimension |
| `lstm.num_layers` | `2` | LSTM stacked layers |
| `lstm.dropout` | `0.2` | LSTM dropout rate |
| `lstm.learning_rate` | `0.001` | LSTM learning rate |
| `lstm.epochs` | `100` | LSTM training epochs |
| `lstm.bidirectional` | `false` | LSTM bidirectional flag |
| `transformer.d_model` | `128` | Transformer model dimension |
| `transformer.nhead` | `4` | Transformer attention heads |
| `transformer.num_encoder_layers` | `3` | Transformer encoder layers |
| `transformer.dim_feedforward` | `512` | Transformer FFN dimension |
| `transformer.dropout` | `0.1` | Transformer dropout rate |
| `transformer.learning_rate` | `0.0005` | Transformer learning rate |
| `transformer.epochs` | `100` | Transformer training epochs |
| `training.device` | `auto` | Training device (auto = CUDA/CPU) |
| `training.loss` | `mse` | Loss function |
| `training.optimizer` | `adam` | Optimizer |
| `training.early_stopping_patience` | `10` | Early stopping patience |
| `evaluation.metrics` | `[rmse, mae, r2, smape]` | Evaluation metrics |
| `export.format` | `torchscript` | Export format |
| `export.export_dir` | `models/exported` | Export directory |

---

## 3. `simulator/configs/twin_config.yaml` — Digital Twin Configuration

**Purpose:** Configures the Digital Twin engine, storage, state validation, and event system.

| Parameter | Default | Description |
|---|---|---|
| `twin.name` | `karnataka_climate_twin` | Twin identifier |
| `twin.version` | `1.0.0` | Twin version |
| `twin.region` | `Karnataka` | Twin region |
| `twin.grid_resolution` | `0.25` | Grid resolution in degrees |
| `storage.engine` | `duckdb` | Storage engine |
| `storage.path` | `data/twin_store` | Storage path |
| `storage.parquet_compression` | `snappy` | Parquet compression codec |
| `state.max_versions_per_entity` | `1000` | Max versions per location |
| `state.enforce_immutable` | `true` | Immutable versioning |
| `state.validate_coordinates` | `true` | Coordinate validation |
| `state.validate_temperatures.min` | `-10` | Minimum valid temperature (°C) |
| `state.validate_temperatures.max` | `55` | Maximum valid temperature (°C) |
| `state.validate_rainfall.min` | `0` | Minimum valid rainfall (mm) |
| `state.validate_rainfall.max` | `2000` | Maximum valid rainfall (mm) |
| `events.enabled` | `true` | Event system enabled |
| `events.max_subscribers` | `50` | Max event subscribers |
| `api.host` | `0.0.0.0` | API bind host |
| `api.port` | `8001` | API port |

---

## 4. `simulator/configs/scenario.yaml` — Scenario Engine Configuration

**Purpose:** Defines scenario validation bounds, simulation parameters, and output configuration.

| Parameter | Default | Description |
|---|---|---|
| `scenarios.temperature.min_delta` | `-5.0` | Min temperature change (°C) |
| `scenarios.temperature.max_delta` | `5.0` | Max temperature change (°C) |
| `scenarios.temperature.step` | `0.5` | Temperature step size |
| `scenarios.temperature.default_increases` | `[1.0, 2.0, 3.0]` | Default temp increase presets |
| `scenarios.rainfall.min_percent_change` | `-100.0` | Min rainfall change (%) |
| `scenarios.rainfall.max_percent_change` | `500.0` | Max rainfall change (%) |
| `scenarios.rainfall.step` | `5.0` | Rainfall step size (%) |
| `scenarios.rainfall.default_increases` | `[10, 20, 40]` | Default rainfall increase presets |
| `scenarios.monsoon.max_delay_days` | `30` | Max monsoon delay (days) |
| `scenarios.monsoon.max_advance_days` | `15` | Max monsoon advance (days) |
| `scenarios.monsoon.intensity_reduction_range` | `[0, 50]` | Intensity reduction range (%) |
| `scenarios.extreme_events.enabled` | `true` | Extreme events enabled |
| `scenarios.extreme_events.types` | `[flood, heatwave, drought]` | Event types |
| `validation.max_combined_scenarios` | `5` | Max combined scenarios |
| `validation.default_duration_days` | `30` | Default simulation duration |
| `simulation.max_execution_ms` | `3000` | Max execution time (ms) |
| `simulation.deterministic` | `true` | Deterministic execution |
| `simulation.random_seed` | `42` | Random seed |
| `output.formats` | `[json, csv, markdown]` | Output formats |
| `output.output_dir` | `simulator/outputs` | Output directory |

---

## 5. `risk/configs/risk.yaml` — Risk Engine Configuration

**Purpose:** Defines risk scoring weights, category thresholds, SHAP explainability, and output settings.

| Parameter | Default | Description |
|---|---|---|
| `risk.score_range.min` | `0` | Minimum risk score |
| `risk.score_range.max` | `100` | Maximum risk score |
| `risk.categories[0]` | Very Low (0-20) | Risk category 1 |
| `risk.categories[1]` | Low (21-40) | Risk category 2 |
| `risk.categories[2]` | Moderate (41-60) | Risk category 3 |
| `risk.categories[3]` | High (61-80) | Risk category 4 |
| `risk.categories[4]` | Severe (81-100) | Risk category 5 |
| `heat.weights.max_temperature` | `0.40` | Heat: max temperature weight |
| `heat.weights.consecutive_hot_days` | `0.35` | Heat: consecutive hot days weight |
| `heat.weights.seasonal_anomaly` | `0.25` | Heat: seasonal anomaly weight |
| `heat.hot_day_threshold_c` | `35` | Hot day threshold (°C) |
| `heat.consecutive_days_threshold` | `3` | Consecutive hot days threshold |
| `flood.weights.rainfall_intensity` | `0.40` | Flood: rainfall intensity weight |
| `flood.weights.multi_day_accumulation` | `0.35` | Flood: multi-day accumulation weight |
| `flood.weights.forecast_uncertainty` | `0.25` | Flood: forecast uncertainty weight |
| `flood.heavy_rain_threshold_mm` | `100` | Heavy rain threshold (mm) |
| `flood.accumulation_window_days` | `3` | Accumulation window (days) |
| `drought.weights.rainfall_deficit` | `0.40` | Drought: rainfall deficit weight |
| `drought.weights.temperature_increase` | `0.30` | Drought: temperature increase weight |
| `drought.weights.dry_period_days` | `0.30` | Drought: dry period weight |
| `drought.deficit_threshold_percent` | `-25` | Deficit threshold (%) |
| `drought.dry_period_threshold_days` | `15` | Dry period threshold (days) |
| `composite.weights.heat` | `0.33` | Composite: heat weight |
| `composite.weights.flood` | `0.33` | Composite: flood weight |
| `composite.weights.drought` | `0.34` | Composite: drought weight |
| `shap.enabled` | `true` | SHAP explanations enabled |
| `shap.max_display_features` | `10` | Max SHAP features to display |
| `shap.background_samples` | `100` | SHAP background samples |
| `output.formats` | `[json, markdown]` | Output formats |
| `output.output_dir` | `risk/outputs` | Output directory |

---

## 6. `knowledge/configs/rag.yaml` — RAG Knowledge Base Configuration

**Purpose:** Configures document chunking, embedding model, FAISS vector store, and retrieval parameters.

| Parameter | Default | Description |
|---|---|---|
| `rag.chunk_size` | `700` | Chunk size (characters) |
| `rag.chunk_overlap` | `120` | Chunk overlap (characters) |
| `rag.embedding_model` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `rag.embedding_dimension` | `384` | Embedding vector dimension |
| `retrieval.top_k` | `5` | Default top-k results |
| `retrieval.score_threshold` | `0.5` | Minimum similarity score |
| `retrieval.enable_metadata_filtering` | `true` | Metadata filtering enabled |
| `vector_store.type` | `faiss` | Vector store type |
| `vector_store.index_path` | `knowledge/vector_store/index.faiss` | FAISS index path |
| `vector_store.metadata_path` | `knowledge/vector_store/metadata.pkl` | Metadata path |
| `documents.base_path` | `knowledge/documents` | Document base directory |
| `documents.supported_formats` | `[pdf, md, txt, csv, json]` | Supported file formats |
| `logging.log_path` | `logs/rag.log` | Log file path |
| `logging.log_level` | `INFO` | Log level |

---

## 7. `copilot/configs/copilot.yaml` — Climate Copilot Configuration

**Purpose:** Controls LLM settings, conversation memory, tool registry, orchestration, and prompt paths.

| Parameter | Default | Description |
|---|---|---|
| `llm.host` | `${OLLAMA_HOST:-http://localhost:11434}` | Ollama host |
| `llm.primary_model` | `qwen3:8b` | Primary LLM model |
| `llm.temperature` | `0.1` | LLM sampling temperature |
| `llm.max_tokens` | `1024` | Max response tokens |
| `llm.context_window` | `8192` | Context window size |
| `memory.type` | `conversation_buffer_window` | Memory type |
| `memory.window_size` | `10` | Conversation turns to retain |
| `memory.expiration_minutes` | `60` | Conversation expiry |
| `orchestration.max_iterations` | `5` | Max tool orchestration steps |
| `orchestration.return_intermediate_steps` | `true` | Return step details |
| `enabled_tools` | `[forecast_tool, digital_twin_tool, scenario_simulator, risk_assessor, rag_retriever, report_generator]` | 6 enabled tools |
| `performance_targets.simple_query_ms` | `2000` | Target: simple query |
| `performance_targets.forecast_ms` | `5000` | Target: forecast query |
| `performance_targets.simulation_ms` | `8000` | Target: simulation query |
| `performance_targets.report_ms` | `10000` | Target: report generation |

### Prompt Templates

| Prompt | Path | Purpose |
|---|---|---|
| Intent Classification | `copilot/prompts/intent.txt` | Classify user intent into 8 types |
| Planning | `copilot/prompts/planner.txt` | Create execution plans |
| Response Generation | `copilot/prompts/generator.txt` | Format responses |
| Error Handling | `copilot/prompts/error.txt` | Error message templates |
