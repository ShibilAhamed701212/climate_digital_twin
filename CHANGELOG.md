# Changelog

## Iteration 4 — Coverage gate achieved: 80.01%

### Fixed
- **validate.py `all_ok` bug**: `False == 0` in Python let boolean `False` pass as "ok". Fixed: `type(v) is int and v == 0` instead of `v == 0`
- **Stale test assertions**: `test_all_pass`/`test_parquet_file` asserted `passed is False` — updated to `True` after `all_ok` bug fix
- **4 uncovered statements covered**: `clean.py:54` (dead code removed), `run_pipeline.py:94-95` (test mock fixed), `simulator/api/main.py:117` (test added)
- **validate.py line 189**: Added `test_check_failure_reports_failed` — covers the `else: failed += 1` path when a validation check genuinely fails

### Results
- Coverage: **80.01%** (2203 of 11019 uncovered) — gate passes
- Tests: **1773 passed**, 18 skipped, **0 failures**
- Ruff: **0 errors**
- No TODOs/FIXMEs in source code
