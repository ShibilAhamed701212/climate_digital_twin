# Forecast Runtime Fix Report

## Root Cause

The gateway image did not install PyTorch. After adding the CPU PyTorch wheel, the next genuine defect was categorical inference: training encoded `Season` with `pd.Categorical().codes`, while production inference passed raw strings and failed with `numpy.object_`.

## Fix

- Added CPU PyTorch to `Dockerfile.gateway`.
- Encoded categorical features identically to training in `ForecastPipeline`.
- Rebuilt and recreated only the gateway forecast path.

## Evidence

- `torch 2.13.0+cpu` imports in the gateway container.
- `POST /forecast/predict` returns HTTP 200.
- Model: `lstm-real-v2`; authenticity: `REAL`.
- Forecast values: rainfall 4.52 mm, Tmax 28.77 C, Tmin 20.59 C.
- Forecast IDs are persisted in `data/forecasts/forecast_history.jsonl`.
