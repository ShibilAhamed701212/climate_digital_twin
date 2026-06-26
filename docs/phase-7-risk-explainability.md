# SYSTEM INSTRUCTION & PROJECT EXECUTION

**Project:** AI-Powered Digital Twin of India's Climate using Indian National Data (ISRO BAH 2026 — Challenge 5)
**Phase Number:** 7
**Phase Name:** Climate Risk Assessment & Explainable AI
**Status:** Completed
**Priority:** Critical
**Estimated Duration:** 5–7 Days
**Dependencies:** ✅ Phase 1 | ✅ Phase 2 | ✅ Phase 3 | ✅ Phase 4 | ✅ Phase 5 | ✅ Phase 6 Completed
**Version:** 1.0
**Document Owner:** Lead ML/Software Engineer
**Last Updated:** 2026-06-26

## 1. GLOBAL AGENT INSTRUCTIONS

## Startup Procedure

Before starting any work:

1. Verify `AGENT.md` exists in the repository root.
2. If missing, create it.
3. Read all previous session logs.
4. Resume from the latest unfinished work.
5. Never overwrite existing logs.
6. Append every work session.
7. Always record:

```text
Phase 7 – Climate Risk Assessment & Explainable AI
```

---

# PHASE OBJECTIVE

Develop an interpretable Climate Intelligence Engine that converts forecasts and simulations into meaningful risk assessments.

This phase has two major responsibilities:

1. Climate Risk Assessment
2. Explainable Artificial Intelligence (XAI)

The outputs from this phase will power:

* Dashboard Risk Maps
* Scenario Impact Reports
* Climate Copilot
* Decision Support

---

# FUNCTIONAL REQUIREMENTS

The system shall:

* Compute Climate Risk Scores.
* Detect potential climate hazards.
* Explain AI predictions.
* Generate district-level risk summaries.
* Produce machine-readable explanations.
* Support downstream RAG retrieval.

---

# NON-FUNCTIONAL REQUIREMENTS

The engine must be:

* Transparent
* Reproducible
* Explainable
* Extensible
* Fast enough for interactive use

---

# ARCHITECTURE

```text
Forecast Engine
        │
        ▼
Digital Twin
        │
        ▼
Risk Assessment Engine
        │
 ┌──────┴───────────┐
 │                  │
 ▼                  ▼
Risk Scores      SHAP Engine
 │                  │
 └──────┬───────────┘
        ▼
Climate Intelligence
        │
        ▼
Dashboard + Copilot
```

---

# DIRECTORY STRUCTURE

```text
risk/

├── engine/
├── scoring/
├── explainability/
├── reports/
├── models/
├── configs/
├── outputs/
└── api/
```

---

# CLIMATE RISK ENGINE

The engine should compute:

* Heat Risk
* Flood Risk
* Drought Risk
* Composite Climate Risk Index

Each score ranges from:

```text
0 – 100
```

Risk categories:

| Score  | Category |
| ------ | -------- |
| 0–20   | Very Low |
| 21–40  | Low      |
| 41–60  | Moderate |
| 61–80  | High     |
| 81–100 | Severe   |

---

# INPUT VARIABLES

Use:

* Rainfall
* Max Temperature
* Min Temperature
* Forecast Confidence
* Historical Trends
* Seasonal Context
* Scenario Adjustments

Future support:

* Soil Moisture
* Humidity
* Vegetation Index
* Reservoir Levels

---

# RISK MODULES

## Heat Risk

Factors:

* Maximum temperature
* Consecutive hot days
* Seasonal anomalies

---

## Flood Risk

Factors:

* Rainfall intensity
* Multi-day accumulation
* Forecast uncertainty

---

## Drought Risk

Factors:

* Rainfall deficit
* Temperature increase
* Long-term dry periods

---

## Composite Climate Risk

Weighted combination of all individual risks.

Weights should be configurable.

---

# EXPLAINABLE AI

Use SHAP as the primary explainability framework.

Objectives:

* Explain individual predictions.
* Explain model behavior.
* Identify important features.
* Increase trust in AI outputs.

---

# REQUIRED EXPLANATIONS

Generate:

* Feature Importance
* Local Explanations
* Global Explanations
* SHAP Summary Plots
* SHAP Waterfall Plots
* SHAP Dependence Plots

---

# EXPLANATION OUTPUT

For every prediction generate:

```text
Prediction

Top Contributing Features

Positive Contributors

Negative Contributors

Confidence

Risk Interpretation
```

---

# CLIMATE INSIGHTS ENGINE

Automatically convert numerical outputs into readable insights.

Example:

```text
Rainfall is expected to decrease by 18%.

Combined with above-average temperatures, this increases drought risk across the selected districts.
```

These insights become inputs for:

* Climate Copilot
* Dashboard
* Reports

---

# REPORT GENERATION

Automatically generate:

* Climate Risk Report
* District Risk Report
* Forecast Interpretation
* SHAP Explanation Report

Formats:

* JSON
* Markdown
* PDF (future)

---

# API CONTRACT

Expose:

```python
calculate_risk()

calculate_heat_risk()

calculate_flood_risk()

calculate_drought_risk()

generate_explanation()

generate_report()

export_results()
```

---

# DASHBOARD INTEGRATION

Display:

* Risk Maps
* District Rankings
* SHAP Charts
* Confidence Indicators
* Climate Insights
* Forecast Explanations

---

# CONFIGURATION

Create:

```text
configs/risk.yaml
```

Contains:

* Risk thresholds
* Weight configuration
* SHAP parameters
* Export settings

---

# LOGGING

Create:

```text
logs/risk_engine.log
```

Log:

* Risk calculations
* SHAP generation
* Report creation
* Errors
* Performance metrics

---

# TESTING REQUIREMENTS

Validate:

* Risk calculations
* SHAP outputs
* Explanation generation
* Report generation
* Dashboard integration
* API responses

---

## CODING STANDARDS
* PEP8 compliant Python with type hints.
* Docstrings on all modules, classes, and functions.
* SOLID principles: scoring, explainability, and reporting as separate concerns.
* Configuration over hardcoding: risk thresholds and SHAP params in YAML.
* Deterministic SHAP explanations (fixed seed).
* Modular design for future risk factor addition.

## QUALITY GATES
Before marking phase complete:
* Run formatter and linter.
* Run all risk engine and SHAP tests.
* Verify risk scores are within 0-100 range.
* Verify SHAP plots generate without errors.
* Verify report generation produces valid output.
* Verify dashboard integration works end-to-end.
* Remove dead code.

## DEFINITION OF DONE
Phase 7 is complete ONLY IF:
* [x] Heat risk module operational.
* [x] Flood risk module operational.
* [x] Drought risk module operational.
* [x] Composite risk index generated.
* [x] SHAP explanations available for predictions.
* [x] Climate insights engine generates readable summaries.
* [x] Reports generated in JSON and Markdown formats.
* [x] `configs/risk.yaml` created.
* [x] `logs/risk_engine.log` enabled.
* [x] Documentation updated and AGENT.md appended.

# DELIVERABLES

* Climate Risk Engine
* Heat Risk Module
* Flood Risk Module
* Drought Risk Module
* Composite Risk Index
* SHAP Integration
* Climate Insights Engine
* Reporting System

---

# ACCEPTANCE CRITERIA

* Heat risk operational.

* Flood risk operational.

* Drought risk operational.

* Composite index generated.

* SHAP explanations available.

* Reports generated.

* Dashboard integration complete.

* Tests passing.

* AGENT.md updated.

---

# PHASE COMPLETION CHECKLIST

* [x] Heat risk module complete

* [x] Flood risk module complete

* [x] Drought risk module complete

* [x] Composite index implemented

* [x] SHAP integration complete

* [x] Climate insights generated

* [x] Reports generated

* [x] Documentation updated

* [x] AGENT.md appended

---

# FUTURE EXTENSIONS

Potential future enhancements:

* Multi-hazard risk modeling
* Vulnerability and exposure analysis
* Population-aware risk estimates
* Infrastructure impact scoring
* Agricultural risk assessment
* Water resource stress indicators
* Economic impact estimation

---

# PROJECT STATUS AFTER PHASE 7

At this point, the project includes:

* ✅ Scope & Architecture
* ✅ Data Pipeline
* ✅ AI Forecasting Engine
* ✅ Digital Twin Core Engine
* ✅ Interactive Dashboard
* ✅ Scenario Simulation Engine
* ✅ Climate Risk Assessment
* ✅ Explainable AI

The remaining planned phases focus on enhancing usability and deployment rather than building the core Digital Twin.

---

# NEXT PHASES (POST-MVP ROADMAP)

## Phase 8 — Climate Knowledge Base & RAG System

Build a retrieval-augmented knowledge system using climate reports, IMD documentation, generated forecasts, and simulation outputs.

## Phase 9 — Climate Copilot

Integrate a lightweight LLM (e.g., Qwen 3 4B) with the RAG pipeline to provide grounded, conversational explanations and decision support.

## Phase 10 — Deployment, Testing & Final Demonstration

Containerize the application, perform end-to-end testing, optimize performance, prepare the final presentation, demo script, technical documentation, and deployment artifacts.
