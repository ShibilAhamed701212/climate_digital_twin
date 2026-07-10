# Known Issues

## Remaining (out of scope for current spec)
- **Medium**: `simulator/historical/computer.py` (92 stmts) — blocked by torch SEH crash on Windows (C++ STATUS_ACCESS_VIOLATION on `import torch`)
- **Low**: `simulator/repository/base.py` (5 stmts) — abstract method `...` bodies, uncoverable
- **Low**: `simulator/api/contract.py` (6 stmts) — abstract method `...` bodies, uncoverable
- **Low**: ~755 dashboard Streamlit stmts — need Streamlit test harness
- **Low**: Docker Desktop not running locally — cannot `docker compose up` for E2E tests
- **Low**: Full `--cov` run crashes on Windows when torch-importing test files execute (partial results still usable)
