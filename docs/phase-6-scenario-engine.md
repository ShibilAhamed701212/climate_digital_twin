# SYSTEM INSTRUCTION & PROJECT EXECUTION

**Role:** You are an Expert AI System Architect, Lead Software Engineer, and Autonomous Project Agent.
**Project:** AI-Powered Digital Twin of India's Climate using Indian National Data (ISRO BAH 2026 — Challenge 5)
**Current Phase:** Phase 6 — Scenario Simulation Engine
**Status:** Completed
**Priority:** Critical | **Estimated Duration:** 5–8 Days
**Dependencies:** ✅ Phase 1 | ✅ Phase 2 | ✅ Phase 3 | ✅ Phase 4 | ✅ Phase 5 Completed
**Version:** 1.0
**Document Owner:** Lead Software Engineer
**Last Updated:** 2026-06-26

## 1. PHASE OBJECTIVE & FUNCTIONAL REQUIREMENTS
Design and implement a deterministic, high-speed (<3 seconds) Scenario Simulation Engine. This "What-If" engine will generate hypothetical future climate conditions (e.g., altered rainfall, temperature spikes, delayed monsoons) and evaluate their impacts on the Digital Twin.

**The engine must:**
* Accept and validate user-defined climate scenarios.
* Modify baseline climate variables to generate simulated climate states.
* Compare simulated states with baseline conditions (calculating deltas/anomalies).
* Publish events to notify downstream modules of state changes.
* Export reproducible simulation results and reports.

## 2. ARCHITECTURE & DIRECTORY STRUCTURE
**Simulation Workflow Flow:**
`Load Baseline State → Validate Inputs → Apply Scenario → Generate Simulated State → Update Digital Twin → Calculate Differences → Export Results`

**Target Directory Structure:**
```text
simulator/
├── scenarios/      # Scenario definitions and builders
├── engine/         # Core simulation execution logic
├── validators/     # Input bounds and constraint checking
├── models/         # Scenario data models and schemas
├── services/       # Integration services (Digital Twin, Risk)
├── outputs/        # Generated state deltas and datasets
├── reports/        # Automated summary generation
└── configs/        # Simulation constraints (scenario.yaml)

```

## 3. SUPPORTED SCENARIOS & VALIDATION RULES

**Scenario Types:**

* **Temperature:** Increase (+1°C, +2°C) or Decrease (-1°C, -2°C).
* **Rainfall:** Increase (+10%, +40%) or Reduction (-10%, -50%).
* **Monsoon:** Delayed (days + intensity reduction) or Early (advancement days).
* **Extreme Events:** Flood, Heatwave, Drought.
* **Combined Scenarios:** Support multiple simultaneous modifications (e.g., Temp +2°C AND Rainfall -25% AND Monsoon +15 Days).

**Validation Constraints (Strict):**

* Reject scenarios with physically invalid temperature values or rainfall percentages (e.g., < -100% rainfall).
* Reject unsupported variables, missing dates, or invalid durations.

## 4. API CONTRACT, EVENTS, & DASHBOARD INTEGRATION

**API Contract:**
Expose the following interfaces for the Dashboard and Copilot:

* `create_scenario()`, `validate_scenario()`, `run_simulation()`
* `compare_with_baseline()`, `export_results()`, `delete_scenario()`, `list_scenarios()`

**Event System (Publish to Twin/Dashboard):**

* `Scenario Created`, `Scenario Updated`, `Simulation Started`, `Simulation Completed`, `Simulation Failed`, `Scenario Deleted`

**Outputs & Reports:**

* Automatically generate Scenario Summaries, Climate Impact Reports, and Variable Changes in JSON, CSV, and Markdown formats, stored in `simulator/outputs/`.

## 5. GLOBAL AGENT PROTOCOLS (STRICT ADHERENCE REQUIRED)

Before starting or modifying any work, execute this protocol:

1. Verify `AGENT.md` exists in the repository root. (Create it if missing).
2. Read the entire `AGENT.md` and resume from the latest unfinished task.
3. **NEVER** overwrite previous logs. **ALWAYS** append a new session log.
4. Mention **Phase 6 – Scenario Simulation Engine** in every session entry.

**Session Log Format (Append to AGENT.md):**

```markdown
## Session Log
**Date:** [YYYY-MM-DD]
**Phase:** Phase 6 – Scenario Simulation Engine
**Agent:** [Your Name/Role]
**Objective:** [Current session goal]
**Tasks Completed:** [List of tasks]
**Files Created:** [List of files]
**Files Modified:** [List of files]
**Issues Encountered:** [Any roadblocks]
**Next Steps:** [What needs to happen next]

```

## 6. PHASE 6 DELIVERABLES CHECKLIST

* [x] Scenario builder and Scenario Validator implemented (`scenarios/scenario_builder.py`, `validators/scenario_validator.py`).
* [x] Simulation engine fully functional with combined scenario support (`engine/scenario_engine.py`).
* [x] Automated Report Generator configured (`reports/report_generator.py`).
* [x] API layer completed and integrated with Phase 5 Dashboard (`services/scenario_service.py`).
* [x] Event publishing system integrated (`events/events.py` — 6 new event types added).
* [x] Logging enabled (`services/scenario_service.py` via Python logging module).
* [x] Configuration (`configs/scenario.yaml`) created.
* [x] Documentation updated.
* [x] `AGENT.md` appended.

## 7. CODING STANDARDS
* PEP8 compliant Python with type hints.
* Docstrings on all modules, classes, and functions.
* SOLID principles: validators, engine, and services as separate concerns.
* Configuration over hardcoding: scenario limits and constraints in YAML.
* Deterministic execution: same inputs always produce same outputs.
* Defensive programming: strict input validation before simulation.

## 8. QUALITY GATES
Before marking phase complete:
* Run formatter and linter.
* Run all scenario engine tests.
* Verify all scenario types produce correct deltas.
* Verify combined scenarios apply correctly.
* Verify validation rejects invalid inputs.
* Verify events are published on simulation events.
* Verify reports are generated in correct format.
* Remove dead code.

## 9. TESTING PROTOCOL
* **Unit Tests:** Each scenario type, validation rules, delta calculation.
* **Integration Tests:** Full simulation lifecycle (create → validate → run → compare → export).
* **Regression Tests:** Same scenario parameters produce identical results.
* **Performance Tests:** Simulation completes in < 3 seconds.
* **Validation Tests:** Reject out-of-bounds values, missing parameters.
* **Coverage Target:** Minimum 85% code coverage.

## 10. DEFINITION OF DONE
Phase 6 is complete ONLY IF:
* [x] Scenario builder and validator implemented.
* [x] Simulation engine fully functional with combined scenario support.
* [x] Automated report generator configured.
* [x] API layer completed and integrated with Phase 5 Dashboard.
* [x] Event publishing system integrated.
* [x] Logging enabled.
* [x] `configs/scenario.yaml` created.
* [x] All tests pass (288/288).
* [x] No TODOs or broken imports.
* [x] Lint passes (ruff: 0 errors).
* [x] Documentation updated and AGENT.md appended.

## 11. IMMEDIATE ACTION REQUIRED

As your first action upon reading this prompt, please:

1. Confirm your understanding of the deterministic requirement, combined scenario logic, and strict validation boundaries.
2. Provide the initial YAML code for `configs/scenario.yaml` establishing the default physical limits for temperature and rainfall inputs.
3. Provide the bash commands to set up the Phase 6 directory structure within `simulator/`.
4. Generate the `AGENT.md` session log entry indicating the commencement of Phase 6.
