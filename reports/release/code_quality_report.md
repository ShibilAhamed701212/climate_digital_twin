# Code Quality Report — BHAI (Bhasha AI)

**Generated:** 2026-06-30  
**Scope:** `runtime/`, `climate/`, `copilot/` modules

---

## 1. Repository Statistics

### File Counts by Module

| Module | Python Files | Lines of Code (excl. tests) |
|--------|-------------|---------------------------|
| `runtime/` | 90 | 7,911 |
| `climate/` | 55 | 3,331 |
| `copilot/` | 7 | 51 |
| **Total** | **152** | **11,293** |

### Non-Python Assets

| Type | Count |
|------|-------|
| YAML configs | 129 |
| Markdown docs | 28 |
| Text files | 18 |
| PNG images | 7 |
| Dockerfile | 1 |
| docker-compose | 1 |
| `.gitignore` | 3 |

### Overall Repository (root)

| Metric | Value |
|--------|-------|
| Total Python files | 162 |
| All files | ~547 |
| Total lines (all .py) | 13,548 |

---

## 2. Test Coverage

| Module | Test Files | Test Lines | Lines of Code | Ratio (test:code) |
|--------|-----------|------------|--------------|-------------------|
| `runtime/` | 29 | 3,772 | 7,911 | **0.48:1** |
| `climate/` | 20 | 1,183 | 3,331 | **0.36:1** |
| **Total** | **49** | **4,955** | **11,293** | **0.44:1** |

---

## 3. Code Complexity

| Module | Functions | Classes | Control Flow Nodes |
|--------|-----------|---------|-------------------|
| `runtime/` | 284 | 93 | 319 |
| `climate/` | 69 | 24 | 166 |
| `copilot/` | 6 | 3 | 0 |
| **Total** | **359** | **120** | **485** |

- **Average complexity per function:** ~1.35 control flow nodes
- **Average functions per class:** ~3.0
- The complexity is well-contained — no excessive nesting observed.

---

## 4. Linting Results (ruff)

**373 errors found** across 3 modules.

| Rule | Count | Severity | Description |
|------|-------|----------|-------------|
| F401 | 167 | Error | Unused imports |
| I001 | 99 | Convention | Unsorted imports |
| E501 | 53 | Error | Line too long |
| B027 | 9 | Warning | Empty method without abstract decorator |
| SIM102 | 7 | Suggestion | Collapsible `if` statements |
| UP031 | 6 | Warning | printf-style string formatting |
| F841 | 5 | Error | Unused variable |
| E402 | 4 | Error | Module import not at top of file |
| UP035 | 4 | Warning | Deprecated import |
| UP042 | 3 | Warning | Replace str/str with enum |
| Others | 16 | Mixed | B007, B905, F541, UP017, UP041, B018, B024, F811, N806, N812, SIM222 |

**207 errors are auto-fixable** with `ruff --fix`.

---

## 5. Type Annotation Coverage

| Metric | Count |
|--------|-------|
| Typed functions (with return annotation) | 329 |
| Untyped functions | 25 |
| **Typing coverage** | **92.9%** |

Excellent type annotation coverage — well above industry standard (>80%).

---

## 6. Code Duplication

| Duplicate Signatures Found | Details |
|---------------------------|---------|
| 3 | `Citation` class (3 files), `ctx()` function (2 files), `make_context()` (2 files) |

Minimal duplication. The `Citation` class appears in `runtime/`, `climate/`, and `copilot/` — consider extracting to a shared library.

---

## 7. Code Quality Score

| Category | Grade | Notes |
|----------|-------|-------|
| Type Safety | **A** | 92.9% annotation coverage |
| Test Coverage | **B+** | 0.44:1 test-to-code ratio, 49 test files |
| Code Complexity | **B** | Well-structured, 359 functions across 120 classes |
| Code Duplication | **A** | Only 3 minor duplicates |
| Linting Cleanliness | **C** | 373 issues, mostly F401 (unused imports) and I001 (import sorting) |
| Documentation Hygiene | **A** | 0 TODO/FIXME/HACK, only 4 NOTE comments |
| **Overall** | **B+** | |

---

## 8. Recommendations

1. **Fix unused imports** (167 F401 errors) — run `ruff --fix runtime/ climate/ copilot/` to auto-remove them. This single fix eliminates 45% of all linting issues.

2. **Sort imports** (99 I001 errors) — run `ruff --fix` to auto-sort. Combined with #1, **207 errors auto-fixable** in one pass.

3. **Extract shared `Citation` class** — the class appears identically in 3 modules. Move to a shared package (`bhai.shared` or similar).

4. **Improve climate test coverage** — current test:code ratio is 0.36:1 vs runtime's 0.48:1. Target 0.50:1.

5. **Line length violations** (53 E501 errors) — configure `ruff` with `line-length = 100` to match common modern Python standards, or reformat.

6. **Address B027 warnings** (9 instances) — empty methods in abstract classes should use `@abstractmethod` decorator.

7. **Run `ruff --fix --unsafe-fixes`** to additionally resolve UP035 (deprecated imports) and UP041 (timeout alias) issues.
