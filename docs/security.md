# Security Architecture

A comprehensive security audit was performed on 2026-06-30 covering `runtime/`, `climate/`, `copilot/`, and root-level Python files. The audit used ripgrep pattern matching, pip-audit dependency scanning, and manual code review.

**Overall Grade: B+**

## Dependency Audit (pip-audit)

8 known vulnerabilities found in build toolchain (pip and wheel), none in runtime dependencies.

| Package | Version | Vulns | Fix Version |
|---------|---------|-------|-------------|
| pip | 23.0.1 | 6 | 26.1.2 |
| wheel | 0.45.1 | 1 | 0.46.2 |

**Note**: These affect build/install tools, not application runtime. Docker image runs Python 3.10 while project requires >=3.11 — a version mismatch flagged for correction.

**Runtime dependencies** (no known CVEs):
- aiohttp >=3.9
- requests >=2.31
- pyyaml >=6.0
- python-dateutil >=2.8
- pydantic >=2.0

## Secret Scanning

| Pattern | Result |
|---------|--------|
| API keys, secrets, passwords | 0 matches |
| JWT secrets | 0 matches |
| Private keys (PEM) | 0 matches |
| Connection strings with passwords | 0 matches |
| Hardcoded public IPs (non-RFC1918) | 0 matches |

**No hardcoded credentials, secrets, or private keys found** in any source files.

## Dangerous Function Analysis

| Function | Status |
|----------|--------|
| `eval()` / `exec()` | 0 actual uses (5 function name matches in test files only) |
| `subprocess.*` | 0 uses |
| `pickle.*` | 0 uses |
| `yaml.load()` | 0 uses (pyyaml is a dependency but unused) |
| `os.system()` / `os.popen()` | 0 uses |
| `mktemp()` | 0 uses |
| `assert` in non-test code | 0 uses |

**No dangerous function calls found in production code.**

## SSRF Analysis

5 HTTP client locations identified:

| File | Target | Risk |
|------|--------|------|
| `climate/providers/scenario.py:33` | `http://scenario-engine:8002` (hardcoded) | Low — Docker internal |
| `copilot_forecast_client.py:24` | `$FORECAST_SERVICE_URL` env var | Medium — env-controllable |
| `copilot_risk_client.py:21` | `$RISK_SERVICE_URL` env var | Medium — env-controllable |
| `07_copilot_chat.py:24,37,46` | `$COPILOT_API_URL` | Low — config-driven |
| `test_dash.py` | `http://copilot-agent:8005` | Low — test only |

**Assessment**: No user-controlled URLs are passed to HTTP clients. All env-var URLs default to Docker-internal service names. SSRF risk is low.

## TOCTOU / Race Condition Analysis

No TOCTOU vectors found. All `open()` calls are in test files. No `os.path.exists()`/`os.access()` patterns used.

## Configuration & Code Quality

- All HTTP calls use explicit timeouts (5-30s)
- No `try: except: pass` patterns — all exceptions handled or logged
- Pydantic models throughout for input validation
- Internal services use HTTP (not HTTPS) — acceptable for Docker-internal communication
- `pyyaml` is listed as a dependency but never used — flagged for removal

## Strengths

- No hardcoded secrets, credentials, or keys
- No use of eval, exec, pickle, subprocess, or unsafe yaml.load
- All HTTP calls use explicit timeouts
- Pydantic models throughout for data validation
- Clean separation of concerns (runtime vs domain)
- Architecture tests prevent domain leaks into runtime core

## Weaknesses

- Docker image runs Python 3.10 but project requires 3.11+
- pip and wheel have 8 known CVEs (build toolchain only)
- HTTP (no TLS) for internal service communication
- Some service URLs controllable via environment variables without validation
- `pyyaml` dependency included but unused — potential future risk if yaml.load is used incorrectly

## Recommendations

1. Upgrade pip and wheel in the Docker image
2. Align Docker Python version with pyproject.toml requirement (3.11+)
3. Add URL validation if env-var-based service URLs can be overridden at deployment
4. Remove unused `pyyaml` dependency or add a linter rule requiring `yaml.safe_load()`
5. Add a CI pipeline step with `pip-audit` or `safety check` for ongoing dependency scanning
6. Consider adding bandit or ruff security rules (`--select S`) for automated security linting

## Full Report

The complete security audit is at `reports/security/security_audit.md` with detailed scan results, patterns, and assessment methodology.
