# Final Runtime Revalidation

## Result

The final operational verification passed **11/11 stages** using `scripts/final_verify.py`.

- Docker services: healthy.
- Provider and observation sync: HTTP 200.
- Twin sync: HTTP 201; gateway state: HTTP 200.
- Forecast models: HTTP 200; REAL+VALIDATED models available.
- Forecast prediction: HTTP 200; `lstm-real-v2`, `REAL`, persisted forecast ID.
- Risk assessment: HTTP 200.
- Scenario service: available.
- Ollama: version 0.32.5 with `qwen3:4b` available.
- Copilot health: HTTP 200; RAG retriever available.
- RAG search: HTTP 200 with indexed Karnataka/India climate sources.
- REAL-store integrity contamination: 0.

## Runtime Repairs

- Forecast dependency/runtime and categorical feature encoding repaired.
- Forecast-engine feature scaling repaired.
- Ollama upgraded from 0.1.32 to a Qwen3-compatible runtime.
- RAG FAISS index rebuilt as the required ID-mapped index and persisted with corrected volume ownership.
- Copilot HTTP timeout and Qwen3 thinking-mode handling repaired.

No synthetic forecasts were added. No database schema, twin architecture, provenance, or integrity scanner changes were made.

## Limitations

- Docker Ollama runs CPU-only because the compose service has no GPU reservation.
- ET0 is explicitly labeled an estimate in the spatial page because the selected view uses hourly T2M rather than daily Tmax/Tmin.
