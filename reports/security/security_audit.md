# Security Audit Report

**Date:** 2026-06-30  
**Scope:** `runtime/`, `climate/`, `copilot/`, `copilot_*.py`, `07_copilot_chat.py`  
**Tooling:** ripgrep (pattern matching), pip-audit (dependency scan), manual code review

---

## 1. Dependency Audit

| Tool | Result |
|------|--------|
| pip-audit | **8 known vulnerabilities found** |

**Vulnerable packages (build/runtime support):**

| Package | Version | Vulnerability | Fix Version |
|---------|---------|--------------|-------------|
| pip | 23.0.1 | PYSEC-2023-228 | 23.3 |
| pip | 23.0.1 | PYSEC-2026-196 | 26.1.2 |
| pip | 23.0.1 | CVE-2025-8869 | 25.3 |
| pip | 23.0.1 | CVE-2026-1703 | 26.0 |
| pip | 23.0.1 | CVE-2026-3219 | 26.1 |
| pip | 23.0.1 | CVE-2026-6357 | 26.1 |
| wheel | 0.45.1 | CVE-2026-24049 | 0.46.2 |

**Note:** These vulnerabilities affect pip and wheel (build/install tools), not the application runtime dependencies. The container runs Python 3.10 while pyproject.toml requires >=3.11 — there is a version mismatch between the Docker image and project specification.

**Runtime dependencies in pyproject.toml:**
- aiohttp >=3.9,<4.0
- requests >=2.31
- pyyaml >=6.0
- python-dateutil >=2.8
- pydantic >=2.0,<3.0

No known runtime dependency CVEs were flagged beyond the pip/wheel build toolchain.

**Recommendation:** Upgrade pip and wheel in the Docker image, and align the Python version in the container with the pyproject.toml requirement (3.11+).

---

## 2. Secret Scanning

| Pattern | Matches | Status |
|---------|---------|--------|
| API keys, secrets, passwords, tokens | 0 | ✅ All clear |
| JWT secrets / super_secret | 0 | ✅ All clear |
| Private keys (PEM) | 0 | ✅ All clear |
| Connection strings with passwords | 0 | ✅ All clear |
| Hardcoded public IPs (non-RFC1918) | 0 | ✅ All clear |

**No hardcoded credentials, secrets, or private keys found** in any source files.

---

## 3. Dangerous Function Usage

| Function | Matches | Status |
|----------|---------|--------|
| `eval()` / `exec()` | 5 | ✅ All matches are function *names* (e.g., `async_exec`, `sync_exec`, `slow_exec`, `failing_exec`, `dict_exec` in test files) — not actual `eval()`/`exec()` calls |
| `subprocess.call/run/Popen/check_call/check_output` | 0 | ✅ Not used |
| `pickle.loads/load/dumps/dump` | 0 | ✅ Not used |
| `yaml.load()` (unsafe) | 0 | ✅ Not used |
| `os.system()` / `os.popen()` | 0 | ✅ Not used |
| `mktemp()` (race condition risk) | 0 | ✅ Not used |
| `assert` in non-test code | 0 | ✅ All `assert` statements are in test files |

**No dangerous function calls found in production code.**

---

## 4. SQL Injection Vectors

| Pattern | Matches | Status |
|---------|---------|--------|
| `cursor.execute()` / `db.execute()` with f-strings | 0 | ✅ Not applicable |
| `cursor.execute()` / `db.execute()` with concatenation | 0 | ✅ Not applicable |

**No SQL usage found.** The codebase does not use SQL databases directly.

---

## 5. SSRF (Server-Side Request Forgery) Analysis

**HTTP client usage found in 5 locations:**

| File | Target URL | Risk |
|------|-----------|------|
| `climate/providers/scenario.py:33` | `http://scenario-engine:8002` (hardcoded) | ✅ Low — internal Docker service |
| `copilot_forecast_client.py:24` | `$FORECAST_SERVICE_URL` env var (default `http://forecast-engine:8006`) | ⚠️ Medium — env-controllable, but default is internal |
| `copilot_risk_client.py:21` | `$RISK_SERVICE_URL` env var (default `http://risk-engine:8003`) | ⚠️ Medium — env-controllable, but default is internal |
| `07_copilot_chat.py:24,37,46` | `$COPILOT_API_URL` (from dashboard config) | ✅ Low — config-driven, internal endpoint |
| `test_dash.py` | `http://copilot-agent:8005` (test file) | ✅ Low — test only |

**Assessment:** No user-controlled URLs are passed directly to HTTP clients. All env-var-based URLs default to Docker-internal service names. SSRF risk is **low** but could be mitigated by validating/constraining the URL schemes and hosts.

---

## 6. TOCTOU / Race Condition Analysis

| Pattern | Matches | Status |
|---------|---------|--------|
| `os.path.exists()` / `os.path.isfile()` / `os.access()` | 0 | ✅ Not used |
| `open()` on file paths (non-test) | 0 | ✅ Not used |

All `open()` calls are in `test_architecture.py` (test file). **No TOCTOU race condition vectors found.**

---

## 7. Configuration & Code Quality

- **pyyaml** is listed as a dependency but `yaml.load()` is never called — appears unused. If yaml parsing is added later, ensure `yaml.safe_load()` is used instead.
- **`requests` calls** use hardcoded timeouts (5-30s) — good practice.
- No use of `try: ... except: pass` — all exceptions are handled or logged.
- The codebase uses Pydantic models for data validation — good for input sanitization.
- `test_ollama.py` and `test_ollama_now.py` use `httpx.Client()` without TLS — these are test scripts and low risk.
- **Internal services use HTTP (not HTTPS)** — acceptable for Docker-internal communication but worth noting.

---

## 8. Overall Security Score

**Grade: B+**

| Category | Score |
|----------|-------|
| Secret exposure | A+ |
| Dangerous functions | A+ |
| SQL injection | A+ (no SQL used) |
| SSRF | B |
| TOCTOU | A+ |
| Dependency hygiene | C |
| Input validation | A- |

### Strengths
- No hardcoded secrets, credentials, or keys
- No use of eval, exec, pickle, subprocess, or unsafe yaml.load
- All HTTP calls use explicit timeouts
- Pydantic models throughout for data validation
- Clean separation of concerns (runtime vs domain)

### Weaknesses
- Docker image runs Python 3.10 but project requires 3.11+
- pip and wheel have 8 known vulnerabilities (build toolchain)
- HTTP (no TLS) used for internal service communication
- Some service URLs controllable via environment variables without validation
- pyyaml dependency included but unused — potential future risk if yaml.load is used incorrectly

### Recommendations
1. Upgrade pip (`pip install --upgrade pip`) and wheel in the Docker image
2. Align Docker Python version with pyproject.toml requirement (3.11+)
3. Add URL validation if env-var-based service URLs can be overridden at deployment
4. Remove unused `pyyaml` dependency, or add a linter rule requiring `yaml.safe_load()`
5. Consider adding a CI pipeline step with `pip-audit` or `safety check` for ongoing dependency scanning
6. Consider adding `bandit` or `ruff` security rules (`--select S`) for automated security linting
