# SYSTEM INSTRUCTION & PROJECT INITIALIZATION

**Project:** AI-Powered Digital Twin of India's Climate using Indian National Data (ISRO BAH 2026 — Challenge 5)
**Phase Number:** 1
**Phase Name:** Scope Definition and System Planning
**Status:** Completed
**Priority:** Critical
**Estimated Duration:** 2–3 Days
**Version:** 1.0
**Document Owner:** Lead ML Engineer
**Last Updated:** 2026-06-26
**Dependencies:** None (Project Initiation Phase)

## 1. PROJECT OBJECTIVES & PROBLEM STATEMENT
Develop a proof-of-concept AI-powered Digital Twin of India's climate system using national datasets. 
This phase establishes the boundaries, goals, datasets, architecture, and deliverables of the project. Outputs from this phase serve as the foundation for all future development.

**The system must:**
* Predict rainfall and temperature.
* Simulate future climate conditions and support scenario analysis.
* Visualize climate conditions via an interactive dashboard.
* Support climate intelligence queries through an AI assistant.

## 2. SCOPE & CONSTRAINTS
### A. Pilot Region
* **Selected Region:** Karnataka
* **Rationale:** Diverse climatic conditions, urban/rural mix, monsoon variability, sufficient meteorological coverage, and manageable MVP scope.
* **Future Expansion:** Kerala, Tamil Nadu, South India, Entire India.

### B. Climate Variables
* **Primary (Current):** Rainfall, Maximum Temperature, Minimum Temperature.
* **Secondary (Future):** Land Surface Temperature, Sea Surface Temperature, Soil Moisture, Humidity.

### C. Prediction Horizon
* 1-Day, 3-Day, and 7-Day Forecasts.

### D. Out of Scope (Do NOT attempt to build)
* National-scale weather forecasting or full atmospheric simulations.
* Supercomputer simulations or high-performance numerical climate models.
* Long-term multi-decade climate projections.

## 3. ARCHITECTURE & TECH STACK
**Proposed Data Flow:**
`National Datasets → Data Pipeline → Feature Engineering → Prediction Models → Digital Twin Engine → Scenario Simulator → Risk Assessment → Climate Copilot → Dashboard`

**Technology Stack:**
* **Data Processing:** Pandas, NumPy
* **Machine Learning:** PyTorch
* **Visualization:** Plotly, Folium
* **Backend:** FastAPI
* **Dashboard:** Streamlit
* **Explainability:** SHAP
* **RAG / AI Assistant:** LangChain, FAISS, Qwen 3 4B (LLM)
* **Deployment:** Docker

**Data Sources:**
* IMD Rainfall: https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html
* IMD Max Temp: https://imdpune.gov.in/cmpg/Griddata/Max_1_Bin.html
* IMD Min Temp: https://www.imdpune.gov.in/cmpg/Griddata/Min_1_Bin.html
* MOSDAC: https://www.mosdac.gov.in/

## 4. REPOSITORY STRUCTURE
Target directory structure to be created:
```text
climate-digital-twin/
├── AGENT.md
├── docs/
├── data/
├── models/
├── backend/
├── dashboard/
├── simulator/
├── notebooks/
└── deployment/

```

## 5. GLOBAL AGENT PROTOCOLS (STRICT ADHERENCE REQUIRED)

Before starting or modifying any work, you must execute the following protocol:

1. Check whether `AGENT.md` exists in the repository root.
2. If `AGENT.md` does not exist, create it.
3. **NEVER** overwrite existing content in `AGENT.md`.
4. **ALWAYS** append new session logs to the bottom of the file.
5. Read the entire `AGENT.md` before beginning work to continue from the latest recorded state.
6. Mention the current phase number in all logs.

**Session Log Format (Append this to AGENT.md at the end of your run):**

```markdown
## Session Log
**Date:** [YYYY-MM-DD]
**Phase:** [Current Phase Number & Name]
**Agent:** [Your Name/Role]
**Tasks Completed:** [List of tasks]
**Modified Files:** [List of files]
**Issues Encountered:** [Any roadblocks]
**Next Steps:** [What needs to happen next]

```

## 6. PHASE 1 DELIVERABLES & SUCCESS CRITERIA

**Mandatory Project Deliverables (MVP):**

* Rainfall & Temperature prediction models.
* Interactive dashboard with Digital Twin visualization.
* Scenario simulator.
* Advanced features: Climate risk score, Explainable AI (SHAP), RAG climate assistant, automated report generation.

**Phase 1 Acceptance Criteria:**

* [x] Pilot region and climate variables finalized.
* [x] Architecture and Tech stack approved.
* [x] Repository structure created and populated with placeholder directories.
* [x] `AGENT.md` initialized.
* [x] Phase documentation completed.

## 7. CODING STANDARDS
* PEP8 compliant Python.
* Type hints on all public functions and methods.
* Docstrings (Google style) on all modules and functions.
* SOLID principles: single responsibility, dependency injection.
* Configuration over hardcoding: no magic numbers or hardcoded paths.
* Reusable modules across phases.
* Production-ready error handling and logging.

## 8. QUALITY GATES
Before marking phase complete:
* Run formatter (black, isort).
* Run linter (flake8 or pylint).
* Verify all configs are externalized.
* Verify all imports resolve correctly.
* Remove dead code and debug statements.
* Perform self-review of all deliverables.

## 9. TESTING PROTOCOL
* **Unit Tests:** Test data loading, validation logic.
* **Integration Tests:** Test pipeline end-to-end.
* **Validation Tests:** Verify outputs meet expected format.
* **Coverage Target:** Minimum 70% code coverage.

## 10. DEFINITION OF DONE
Phase 1 is complete ONLY IF:
* [x] Pilot region and climate variables finalized.
* [x] Architecture and Tech stack approved.
* [x] Repository structure created and populated with placeholder directories.
* [x] AGENT.md initialized.
* [x] Phase documentation completed.
* [x] All acceptance criteria satisfied.
* [x] No broken references or missing dependencies.

## 11. IMMEDIATE ACTION REQUIRED

As your first action upon reading this prompt, please:

1. Confirm your understanding of the scope, out-of-scope boundaries, and operational protocols.
2. Generate the exact initial text content for `AGENT.md`, including the first Session Log confirming the completion of Phase 1 planning.
3. Provide the bash commands to generate the repository directory structure.
4. State that you are ready to transition to **Phase 2 — Data Collection and Data Pipeline**.
