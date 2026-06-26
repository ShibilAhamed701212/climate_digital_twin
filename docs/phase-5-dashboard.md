# SYSTEM INSTRUCTION & PROJECT EXECUTION

**Project:** AI-Powered Digital Twin of India's Climate using Indian National Data (ISRO BAH 2026 — Challenge 5)
**Phase Number:** 5
**Phase Name:** Geospatial Visualization & Digital Twin Dashboard
**Status:** Completed
**Priority:** High
**Estimated Duration:** 5–7 Days
**Dependencies:** ✅ Phase 1 | ✅ Phase 2 | ✅ Phase 3 | ✅ Phase 4 Completed
**Version:** 1.0
**Document Owner:** Lead Full-Stack Engineer
**Last Updated:** 2026-06-26

## 1. PHASE OBJECTIVE & DESIGN PRINCIPLES
Develop an interactive Digital Twin Dashboard that visualizes current climate conditions, historical trends, forecasts, the Digital Twin state, climate risks, and future scenarios. The dashboard must enable intuitive exploration of the pilot region using interactive maps, charts, and analytics.

**Design Principles:** Interactive, Responsive, Intuitive, Scientific, Accessible, Modular, Extensible.

## 2. TECHNOLOGY STACK & ARCHITECTURE
**Tech Stack:**
* **Frontend:** Streamlit
* **Visualization:** Plotly, Folium, GeoPandas
* **Backend API:** FastAPI
* **Maps:** OpenStreetMap, Leaflet (via Folium)

**Target Directory Structure:**
```text
dashboard/
├── app.py          # Main entry point
├── pages/          # Multi-page application routing
├── components/     # Reusable UI widgets (cards, sidebars)
├── charts/         # Plotly visualization logic
├── maps/           # Folium/GeoPandas map logic
├── services/       # API clients and data fetchers
├── assets/         # Static assets (CSS, images)
├── themes/         # Streamlit styling/theming
└── config/         # App configuration and constants
```

## 3. DASHBOARD PAGES & FEATURES

### Page 1: Climate Overview
* Interactive map of Karnataka with color-coded climate variables.
* Current conditions: rainfall, max/min temperature.
* District-level data on hover/click.
* Time-series selector for historical view.

### Page 2: Forecast Viewer
* 1-day, 3-day, and 7-day forecast maps.
* Confidence indicators for predictions.
* Side-by-side comparison with current conditions.
* Download forecast data.

### Page 3: Digital Twin State
* Current, historical, and forecast state layers.
* State version timeline.
* Grid cell detail view with all attributes.
* State transition log viewer.

### Page 4: Scenario Simulator
* Scenario parameter inputs (temperature delta, rainfall % change).
* Before/after comparison maps.
* Delta/anomaly visualization.
* Scenario impact summary cards.

### Page 5: Climate Risk
* Risk score map (heat, flood, drought, composite).
* District ranking table.
* Risk trend charts over time.
* SHAP explanation panels for predictions.

### Page 6: Reports & Insights
* Auto-generated climate reports.
* District-level summaries.
* Exportable charts and data.
* PDF report generation trigger.

## 4. DATA FLOW
```
FastAPI Backend (Phase 4 + 6 + 7)
         │
         ▼
dashboard/services/api_client.py
         │
         ▼
dashboard/pages/*.py
         │
    ┌────┴────┐
    ▼         ▼
charts/    maps/
    │         │
    └────┬────┘
         ▼
    Streamlit Renderer
```

## 5. SYSTEM INITIALIZATION PROTOCOL
Before any implementation:
1. Verify `AGENT.md` exists. Create if missing.
2. Read entire `AGENT.md` to determine latest completed work.
3. Inspect repository: verify `dashboard/` subdirectories exist.
4. Verify dependencies: Streamlit, Plotly, Folium, GeoPandas, requests.
5. Verify FastAPI backend is operational (Phase 4).
6. Build execution plan with page implementation order.
7. Never overwrite logs. Always append session logs.
8. Mention **Phase 5 – Geospatial Visualization & Digital Twin Dashboard** in every session entry.

## 6. GLOBAL AGENT PROTOCOLS (STRICT ADHERENCE REQUIRED)
* Check `AGENT.md` exists; create if missing.
* Read full history; resume from latest unfinished task.
* Never overwrite previous logs; always append.
* Generate implementation summary after each session.
* Generate completion report before phase sign-off.

**Session Log Format:**
```markdown
## Session Log
**Date:** [YYYY-MM-DD]
**Phase:** Phase 5 – Geospatial Visualization & Digital Twin Dashboard
**Agent:** [Your Name/Role]
**Objective:** [Current session goal]
**Tasks Completed:** [List of tasks]
**Files Created:** [List of files]
**Files Modified:** [List of files]
**Issues Encountered:** [Any roadblocks]
**Next Steps:** [What needs to happen next]
```

## 7. IMPLEMENTATION PLANNING
Before coding, generate:
* **Current State:** What exists in `dashboard/`, `backend/`.
* **Missing Components:** Page modules, chart components, map layers, API client.
* **Dependency Graph:** Backend API → API Client → Pages → Charts/Maps.
* **Execution Plan:** Page implementation order (Overview → Forecast → Twin → Scenario → Risk → Reports).
* **Risk Assessment:** API availability, map rendering performance, data volume.
* **Estimated Work:** LoC estimates per page and component.

## 8. CODING STANDARDS
* PEP8 compliant Python.
* Type hints on all public functions.
* Docstrings on all modules and components.
* Modular design: each page in separate file, reusable chart/map components.
* Configuration over hardcoding: API URLs, map defaults, color schemes in config.
* Responsive design considerations for Streamlit.
* Error handling for API failures (graceful fallbacks).

## 9. QUALITY GATES
Before marking phase complete:
* Run formatter and linter.
* Test all pages render without errors.
* Verify all API integrations work end-to-end.
* Verify map tiles load correctly.
* Verify charts display data correctly.
* Test with sample/mock data.
* Remove debug code.
* Verify imports resolve.
* Generate implementation summary.

## 10. TESTING PROTOCOL
* **Unit Tests:** Component rendering tests, data transformation tests.
* **Integration Tests:** Page loads with mock API responses, map rendering.
* **Regression Tests:** Verify UI consistency across runs.
* **Performance Tests:** Page load times (< 3s), map interaction responsiveness.
* **Validation Tests:** Verify displayed data matches API response.

## 11. API CONTRACT
**Dashboard consumes from FastAPI backend:**
* `GET /api/v1/current?location_id={id}`
* `GET /api/v1/forecast?location_id={id}&horizon={days}`
* `GET /api/v1/historical?location_id={id}&start={date}&end={date}`
* `GET /api/v1/scenarios/list`
* `GET /api/v1/risk?location_id={id}`
* `POST /api/v1/scenarios/simulate`

**Response Format:** JSON with standardized envelope `{status, data, metadata, timestamp}`.

## 12. DELIVERABLES CHECKLIST
* [x] Main `app.py` entry point with multi-page routing
* [x] Climate Overview page with interactive map
* [x] Forecast Viewer page with prediction maps
* [x] Digital Twin State page with version timeline
* [x] Scenario Simulator page with before/after comparison
* [x] Climate Risk page with SHAP panels
* [x] Reports & Insights page
* [x] Reusable chart components (Plotly)
* [x] Reusable map components (Folium)
* [x] API client service module
* [x] Dashboard configuration file
* [x] Tests for all pages
* [x] Logging operational (via `logging` module in services/api_client.py)
* [x] Documentation updated
* [x] `AGENT.md` appended

## 13. DEFINITION OF DONE
Phase 5 is complete ONLY IF:
* [x] All 6 dashboard pages render correctly and are navigable.
* [x] Interactive map displays Karnataka with climate data overlay.
* [x] Forecast, scenario, and risk pages consume real backend APIs (with synthetic fallback).
* [x] Charts and visualizations are accurate and responsive.
* [x] All tests pass (215/215).
* [x] No TODO markers remain.
* [x] Lint passes (ruff: 0 errors).
* [x] Acceptance criteria satisfied.
* [x] Documentation updated and AGENT.md appended.

## 14. NEXT PHASE
**Phase 6 — Scenario Simulation Engine:** Powers the Scenario Simulator page with "What-If" analysis capabilities.
