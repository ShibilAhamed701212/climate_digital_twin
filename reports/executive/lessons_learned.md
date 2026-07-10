# Lessons Learned

## 1. Audit-First Approach (42 → 72/100)

During Phase 10 deployment hardening, an audit of all 8 Dockerfiles revealed that every one referenced non-existent Python modules or had incorrect CMD targets. The original bootstrap phase had created Dockerfiles as placeholders without validating they could actually start. The lesson: **never assume bootstrapped infrastructure is correct** — audit every file before relying on it. Code quality scores improved from 42/100 to 72/100 after fixing issues across all 8 Dockerfiles and 6 API `main.py` modules.

## 2. One Logical Fix Per Loop

When iterating on test fixes, the most efficient pattern was to identify the single root cause, fix it, re-run, and repeat. Trying to batch multiple speculative fixes led to confusion about which change actually resolved which failure. The AGENT.md logs show this pattern consistently across all 10 phases — fixing one thing at a time, verifying with the full test suite, then moving to the next.

## 3. NumPy/Pandas Version Pinning Importance

The project encountered 18 known test failures caused entirely by dependency version mismatches in the local development environment (not in the code):
- **NumPy 2.x** removed `np.long`, breaking SciPy → Plotly chain
- **FAISS** built for NumPy 2.x imports `numpy._core` which doesn't exist in NumPy 1.26.0
- **Streamlit/Starlette** version incompatibility broke `starlette.middleware.gzip`

**Lesson:** Always pin exact dependency versions in `pyproject.toml` and Dockerfiles. The containerized environment (Docker) is the source of truth — local development environments will always drift. Document known failures as a regression baseline so new vs pre-existing failures can be distinguished at a glance.

## 4. Docker vs Local Development Strategy

Developing complex multi-service systems locally without Docker leads to environment-specific failures (18 in this project). The recommended workflow is:
- **Business logic & unit tests** → develop locally with `make test`
- **Integration & deployment** → always test inside Docker containers
- **Demo** → always run via `docker compose up` or `bash deployment/scripts/demo.sh`

The `known_failures.md` baseline document was created specifically to track environment-induced failures vs code regressions.

## 5. Ollama Model Name Validation

The copilot config specified `qwen3:8b` as the primary model, but earlier iterations used `qwen:4b`. When switching LLMs, the model name must exactly match what Ollama expects (`ollama list` to verify). The temperature was set to 0.1 for deterministic output, and the context window to 8192 tokens.

## 6. Global Cache Anti-Pattern in Config Loaders

The copilot config loader initially used a global cache (`@lru_cache`) that caused unit tests with custom config paths to return default values instead. **Fix:** Skip caching when an explicit path is provided. Config loaders should support both cached (production) and non-cached (testing) modes.

## 7. Windows-Specific Issues

- **PowerShell 5.1** `Join-Path` does not support 3+ segments — worked around with string interpolation
- **Unicode Δ character** (U+0394) in simulator reports caused `cp1252` encoding errors on Windows — replaced with "delta" text and set explicit UTF-8 encoding
- **`functools.lru_cache`** on Windows has different behavior than Linux for recursive calls

## 8. Pre-Commit and Linting Discipline

The project used `ruff` with strict rules (E, F, W, I, N, UP, B, SIM, ARG) and a pre-commit hook. Common issues caught:
- `B011` — `assert False` in tests (use `pytest.raises` instead)
- `B904` — missing `from err` in raise chains
- `B905` — missing `strict=True` in `zip()`
- `F841` — unused variables
- `ARG002` — unused method parameters
- `N999` — Streamlit page files with numeric prefixes (suppressed with `# noqa: N999` per convention)

## 9. Synthetic Data Fallback for Hackathon Environments

Every service includes deterministic synthetic data fallback so the system runs without any external API dependencies. This was critical for the hackathon context where internet access may be limited. The fallback generates:
- Realistic grid data from NASA POWER API structure
- Dummy embeddings for FAISS (stable random, configurable dimension)
- Deterministic SHAP estimation instead of actual model calls
- Pre-cached model checkpoints with fixed predictions

## 10. Sequence of Service Creation Matters

In AGENT.md, the development followed a strict phase order (1→10) because each phase depended on the previous:
1. Scope → 2. Data → 3. Forecast → 4. Twin → 5. Dashboard → 6. Scenario → 7. Risk → 8. RAG → 9. Copilot → 10. DevOps

The dashboard (Phase 5) came before scenario/risk/RAG (Phases 6-8) because it could be built with mock data. The Copilot (Phase 9) was built last because it depends on all downstream services. This ordering minimized blocking dependencies.
