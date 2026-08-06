# Phase 3 Corrective Implementation Status

## Objective
Correct Phase 3 ML training bugs discovered during audit: fix config selection, add feature scaling for neural models, invalidate broken LSTM checkpoint, retrain from scratch, and scientifically re-verify all results.

## Completed
- **trainer.py**: Added `_ARCH_TO_CONFIG` mapping, `_resolve_model_config()`, `model_type` parameter to `train_model()`. Unknown model type raises `ValueError`. LSTM now gets LSTM config (epochs=100), not baseline (epochs=50).
- **data_loader.py**: Added `NEURAL_FAMILIES`, `needs_scaling()`, `scale` parameter to `load_data()`. When `scale=True`, features+targets min-max scaled using TRAIN-only statistics before creating ClimateDataset. Returns scalers alongside loaders.
- **data_loader.py**: Added `save_scalers()` / `load_scalers()` — pickle files alongside checkpoints.
- **registry.py**: Added `status` field (`EXPERIMENTAL`/`VALIDATED`/`REJECTED`), `update_status()`, `RegistryError`, `get_best(require_validated=True)`. `register()` defaults to `EXPERIMENTAL`.
- **evaluator.py**: Added `compute_per_target_metrics()` (dict keyed by target name), `detect_collapse()` (checks pred_std / target_std ratio < 0.1), `target_scaler` parameter to `evaluate_model()` (inverse-transforms to physical units before computing metrics).
- **forecast_cli.py**: Rewritten — `cmd_train` passes `model_type` to `train_model()`, uses `needs_scaling()`, saves scalers when scaling, checks collapse, sets status. `cmd_forecast` loads persisted scalers, applies feature scaling before predict + target inverse transform after.
- **lstm-real-v1 invalidated**: `status=REJECTED`, `reason=MODEL_COLLAPSE / TRAINING_PREPROCESSING_BUG`.
- **lstm-real-v2 retrained**: Correct LSTM config (100 epochs, hidden_dim=128, num_layers=2), scaled data. Status=VALIDATED. Per-target: Rainfall RMSE=2.9864 R²=-0.0378, MaxTemp RMSE=1.2235 R²=0.8504, MinTemp RMSE=0.9854 R²=0.8713.
- **Final eval**: 7 models on 245-test-sample set. LSTM-real-v2 best by R² sum (1.68). Baseline-real-v1 second (1.51). No collapse in corrected models.
- **Registry statuses**: baseline-real-v1 → VALIDATED, lstm-real-v2 → VALIDATED, synthetic models → EXPERIMENTAL, lstm-real-v1 → REJECTED.
- **Regression tests** (test_phase3_corrections.py): 19/19 pass — config mapping, scalers, collapse detection, per-target metrics, registry status, forecast provenance.

## Active Issues
- torch DLL crash (access violation) on Windows when conftest.py imports torch at module level during collection. Pre-existing environment issue, not from Phase 3 changes. Mitigated by running tests individually or using subprocess pattern.

## Blocked
- None

## Next Move
1. Fresh-process checkpoint test: load lstm-real-v2 from registry in clean process, load persisted scalers, generate forecast.
2. Full E2E forecast: REAL data → REAL Twin → production model → forecast → physics validation → ForecastStore.
3. Verify observed Twin unchanged after forecast (StateType isolation proof).
4. Compile final corrective report.

## Relevant Files
- `models/trainer.py`: `_ARCH_TO_CONFIG`, `_resolve_model_config()`, `model_type` param
- `models/data_loader.py`: `NEURAL_FAMILIES`, `needs_scaling()`, `save_scalers()`, `load_scalers()`, `scale` param
- `models/registry.py`: `status`, `update_status()`, `RegistryError`, `get_best(require_validated=True)`
- `models/evaluator.py`: `compute_per_target_metrics()`, `detect_collapse()`, `target_scaler` param
- `models/forecast_cli.py`: rewritten with config selection, scaling, collapse, scaler persistence
- `tests/unit/models/test_phase3_corrections.py`: 19 regression tests (subprocess pattern)
- `models/registry/metadata.json`: 7 entries — lstm-real-v1 (REJECTED), lstm-real-v2 (VALIDATED), baseline-real-v1 (VALIDATED), 3 synthetic (EXPERIMENTAL)
- `models/checkpoints/lstm-real-v2_best.pt`: Corrected LSTM checkpoint
- `models/checkpoints/lstm-real-v2_feat_scaler.pkl`, `lstm-real-v2_tgt_scaler.pkl`: Persisted scalers
