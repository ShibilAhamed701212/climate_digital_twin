# SYSTEM INSTRUCTION & PROJECT EXECUTION

**Project:** AI-Powered Digital Twin of India's Climate using Indian National Data (ISRO BAH 2026 — Challenge 5)
**Phase Number:** 3
**Phase Name:** AI Forecasting Engine
**Status:** Completed
**Priority:** Critical
**Estimated Duration:** 6–8 Days
**Dependencies:** ✅ Phase 1 Completed | ✅ Phase 2 Completed
**Version:** 1.0
**Document Owner:** Lead ML Engineer
**Last Updated:** 2026-06-26

## 1. PHASE OBJECTIVES & FUNCTIONAL REQUIREMENTS
Develop an extensible, highly modular AI forecasting engine capable of predicting key climate variables for the selected pilot region.

**The forecasting engine must:**
* Accept processed, cleaned datasets exported from Phase 2.
* Train, evaluate, and compare multiple forecasting architectures (Baseline, LSTM, Transformer).
* Produce deterministic, standardized predictions for downstream systems.
* Support GPU acceleration and be highly reproducible (enforce fixed random seeds).
* Expose a unified Prediction API contract that hides model complexities from the Digital Twin engine.

## 2. DIRECTORY STRUCTURE & MODEL REGISTRY
**Target Directory Structure:**
```text
models/
├── baseline/         # Simple benchmark models
├── lstm/             # Deep-learning sequence baseline
├── transformer/      # Advanced temporal forecasting
├── checkpoints/      # Intermediate training weights
├── exported/         # Production-ready compiled models (.pt, TorchScript)
├── evaluation/       # Metrics, JSONs, and generated plots
└── configs/          # YAML configurations
```

## 3. PIPELINE ARCHITECTURE & MODULES
**Training Pipeline:**
`Data Load → Preprocessing → Model Selection → Training → Evaluation → Export → Prediction`

### Module 1: Data Loader
* Load processed train/val/test splits from `data/processed/`.
* Create PyTorch `Dataset` and `DataLoader` with configurable batch size and sequence length.
* Support feature scaling and target normalization.

### Module 2: Model Registry
* Baseline: Simple feed-forward or linear model for benchmark comparison.
* LSTM: Sequence model with configurable layers, hidden dimensions, and dropout.
* Transformer: Temporal Transformer encoder with positional encoding.

### Module 3: Training Engine
* Support GPU/CPU training with automatic device detection.
* Configurable loss functions (MSE, MAE), optimizers (Adam, SGD), and schedulers.
* Early stopping, model checkpointing, and training metrics logging.
* Fixed random seeds for full reproducibility.

### Module 4: Evaluation
* Compute metrics: RMSE, MAE, R², MAPE.
* Generate plots: predictions vs actuals, error distribution, residuals.
* Compare across all model architectures.
* Export evaluation reports to `models/evaluation/`.

### Module 5: Prediction API
* Load best-performing model from checkpoint.
* Standardized prediction interface: `predict(location_id, horizon, variables)`.
* Return predictions with confidence intervals.
* Output format: JSON with timestamps, predicted values, and metadata.

## 4. MODEL CONFIGURATION
**Required YAML config (`models/configs/model_config.yaml`):**
* Data parameters: sequence length, batch size, feature columns, target columns.
* Model parameters: architecture selection, hidden layers, dropout, learning rate.
* Training parameters: epochs, early stopping patience, validation frequency.
* Evaluation parameters: metrics, visualization flags.
* Export parameters: TorchScript compilation, export path.

## 5. SYSTEM INITIALIZATION PROTOCOL
Before any implementation:
1. Verify `AGENT.md` exists in repository root. Create if missing.
2. Read entire `AGENT.md` to determine latest completed work.
3. Inspect repository: verify `models/` subdirectories, check `data/processed/` exists.
4. Verify Python packages: PyTorch, NumPy, Pandas, Matplotlib, scikit-learn.
5. Build execution plan with dependency graph.
6. Execute only Phase 3 tasks.
7. Never overwrite logs. Always append session logs.
8. Mention **Phase 3 – AI Forecasting Engine** in every session entry.

## 6. GLOBAL AGENT PROTOCOLS (STRICT ADHERENCE REQUIRED)
* Check `AGENT.md` exists; create if missing.
* Read full history; resume from latest unfinished task.
* Never overwrite previous logs; always append.
* Mention current phase in all session entries.
* Generate implementation summary after each session.
* Generate completion report before phase sign-off.

**Session Log Format:**
```markdown
## Session Log
**Date:** [YYYY-MM-DD]
**Phase:** Phase 3 – AI Forecasting Engine
**Agent:** [Your Name/Role]
**Objective:** [Current session goal]
**Tasks Completed:** [List of tasks]
**Files Created:** [List of files]
**Files Modified:** [List of files]
**Issues Encountered:** [Any roadblocks]
**Next Steps:** [What needs to happen next]
```

## 7. IMPLEMENTATION PLANNING
Before coding, generate:
* **Current State:** What exists in `models/`, `data/processed/`.
* **Missing Components:** Data loaders, model classes, training scripts, evaluation.
* **Dependency Graph:** Phase 2 output → DataLoader → Model → Training → Evaluation.
* **Execution Plan:** Order of module implementation.
* **Risk Assessment:** Data quality issues, convergence problems, GPU availability.
* **Estimated Work:** LoC estimates per module.

## 8. CODING STANDARDS
* PEP8 compliant Python.
* Type hints on all public functions and methods.
* Docstrings (Google style) on all modules, classes, and functions.
* SOLID principles: Single responsibility per module, dependency injection for configs.
* Configuration over hardcoding: no magic numbers, paths, or hyperparameters in code.
* Reusable modules: models should be independent of data sources.
* Production-ready: error handling, logging, graceful degradation.

## 9. QUALITY GATES
Before marking phase complete:
* Run formatter (black, isort).
* Run linter (flake8 or pylint).
* Run all unit and integration tests.
* Perform self-review of all code.
* Remove dead code and debug statements.
* Verify all configs are externalized.
* Verify all imports resolve correctly.
* Verify API contracts match documentation.
* Verify evaluation metrics are generated.
* Generate implementation summary.

## 10. TESTING PROTOCOL
* **Unit Tests:** Test each model forward pass, data loader shapes, loss computation.
* **Integration Tests:** Train for 1 epoch on sample data, verify loss decreases.
* **Regression Tests:** Verify same seed produces identical outputs.
* **Performance Tests:** Benchmark training time, inference latency.
* **Validation Tests:** Verify predictions are within physically possible ranges.
* **Coverage Target:** Minimum 80% code coverage.

## 11. API CONTRACT
**Prediction API:**
* `load_model(model_name: str, checkpoint_path: str) -> nn.Module`
* `predict(model, input_data: torch.Tensor) -> dict`
* `train_model(config: dict, data: tuple) -> dict`
* `evaluate_model(model, data_loader) -> dict`
* `export_model(model, path: str) -> None`

**Inputs:** Sequence of historical climate variables (Rainfall, MaxTemp, MinTemp).
**Outputs:** Predicted values with confidence scores, timestamps.
**Exceptions:** `ModelNotFoundError`, `DataShapeError`, `PredictionError`.
## 12. DELIVERABLES CHECKLIST

* [x] Data loader module implemented
* [x] Baseline model trained and evaluated
* [x] LSTM model trained and evaluated
* [x] Transformer model trained and evaluated
* [x] Model comparison report generated
* [x] Best model exported to `models/exported/`
* [x] Prediction API implemented
* [x] Model configuration created (`models/configs/model_config.yaml`)
* [x] Evaluation plots and metrics saved
* [x] Logging operational
* [x] Tests passing
* [x] Documentation updated
* [x] `AGENT.md` appended

## 13. DEFINITION OF DONE
Phase 3 is complete ONLY IF:
* [x] All three model architectures are implemented and trained.
* [x] Evaluation metrics (RMSE, MAE, R²) are generated and compared.
* [x] Best model is exported in TorchScript format.
* [x] Prediction API returns correct structured output.
* [x] All tests pass.
* [x] No TODO markers remain in code.
* [x] No broken imports exist.
* [x] Lint passes without errors.
* [x] All acceptance criteria satisfied.
* [x] Documentation updated and AGENT.md appended.

## 14. NEXT PHASE
**Phase 4 — Digital Twin Core Engine:** Consumes forecast outputs to maintain dynamic climate state.
