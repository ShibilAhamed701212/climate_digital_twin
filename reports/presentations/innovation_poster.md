# Innovation Poster (Text Format)

> **⚠️ Honest version. Proof-of-concept. Synthetic data. Mock copilot.**

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║         AI-POWERED DIGITAL TWIN OF INDIA'S CLIMATE (PROTOTYPE)                  ║
║         ISRO BAH 2026 — Challenge 5 | July 2026 | v0.1.0 — Proof-of-Concept    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│  WHAT WE BUILT                                                                   │
│                                                                                  │
│  A prototype architecture for a climate digital twin: 8 Docker services,         │
│  8-step data pipeline, 3 trained models, and an interactive dashboard.           │
│                                                                                  │
│  ⚠️ HONESTY NOTE: All data is synthetic (np.random.seed(42)). Copilot returns   │
│  mock template responses (no LLM wired). FAISS index starts empty.              │
│  This is a proof-of-concept for the architecture, not a production system.      │
│                                                                                  │
│  Pilot: 15 sample Karnataka districts (hardcoded in config.yaml)                 │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  PROBLEM                                                                         │
│                                                                                  │
│  India loses 3-5% of GDP annually to climate-related disasters.                 │
│  Climate data exists but is fragmented and not integrated.                       │
│                                                                                  │
│  Key Question: Can we design the architecture for a unified system that:        │
│    • Predicts rainfall and temperature                                          │
│    • Simulates what-if climate scenarios                                        │
│    • Assesses heat, flood, and drought risk                                     │
│    • Answers natural language queries                                           │
│    • Deploys with one command?                                                  │
│                                                                                  │
│  Answer: Architecture designed ✅. Real data integration: NEXT.                   │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  ARCHITECTURE (8 Docker Services)                                                │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    STREAMLIT DASHBOARD (8501)                            │   │
│  │            7 live pages + 3 mock pages | Folium | Plotly                 │   │
│  └────────────────────────────────┬─────────────────────────────────────────┘   │
│                                   │                                              │
│  ┌────────────────────────────────▼──────────────────────────────────────────┐   │
│  │                     NGINX REVERSE PROXY (80)                              │   │
│  └──┬──────────┬──────────┬──────────┬──────────┬──────────┬─────────────────┘   │
│     │          │          │          │          │          │                     │
│     ▼          ▼          ▼          ▼          ▼          ▼                     │
│  ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐              │
│  │ TWIN │ │FORECAST│ │SCENARIO│ │  RISK  │ │  RAG   │ │ COPILOT  │              │
│  │8002  │ │ 8005   │ │ 8003   │ │ 8004   │ │ 8006   │ │ 8007     │              │
│  │Real: │ │Real: 3 │ │Real:   │ │Real:   │ │⚠️Empty │ │⚠️Mock    │              │
│  │synth │ │models  │ │11      │ │4 scores│ │index   │ │responses │              │
│  │state │ │+3 stubs│ │presets │ │        │ │        │ │          │              │
│  └──────┘ └────────┘ └────────┘ └────────┘ └────────┘ └──────────┘              │
│                                                                                  │
│  Ollama (Qwen3:8b) — declared but NOT WIRED to copilot                          │
│  Prometheus + Grafana — defined but NOT actively configured                      │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  DATA: ALL SYNTHETIC                                                             │
│                                                                                  │
│  Declared: NASA POWER API — 43 years, 48 grid cells                              │
│  Actual:   np.random.seed(42) — random values in correct schema                  │
│                                                                                  │
│  Pipeline: Generate → Validate → Feature Engineering → Export                    │
│                                                                                  │
│  Output: 628,200 synthetic rows | 70/15/15 split                                 │
│  Quality: 0 missing values (expected from generated data)                        │
│                                                                                  │
│  ⚠️ NASA POWER download code exists but always uses synthetic fallback           │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  KEY INNOVATIONS (with honest status)                                            │
│                                                                                  │
│  1. 3 TRAINED MODELS + 4 STUBS                                                  │
│     LSTM (RMSE 4.53), Transformer (4.57), MLP (4.59) — ON SYNTHETIC DATA        │
│     PatchTST, TimeMixer, iTransformer — class definitions only (stubs)           │
│     Ensemble — not trained. All three show suspiciously uniform R²=0.87          │
│     PhysicsValidator enforces basic physical constraints                         │
│                                                                                  │
│  2. DIGITAL TWIN WITH IMMUTABLE VERSIONING                                      │
│     Append-only state manager, EventBus pub/sub                                 │
│     Clean, production-quality design — strongest component                       │
│     All states are synthetic                                                     │
│                                                                                  │
│  3. SCENARIO SIMULATION ENGINE                                                   │
│     5 types, 11 presets, deterministic <3s                                       │
│     Linear perturbations of synthetic baseline                                   │
│                                                                                  │
│  4. RISK SCORING (4 MODULES)                                                     │
│     Heat, Flood, Drought, Composite — configurable weights                       │
│     ⚠️ SHAP is deterministic synthetic — not connected to model gradients        │
│     ⚠️ Risk thresholds arbitrary — not calibrated                                │
│                                                                                  │
│  5. RAG KNOWLEDGE BASE                                                           │
│     FAISS IndexFlatIP, 15 docs → 30 chunks                                      │
│     ⚠️ Index starts EMPTY. generate_answer() is MOCK                             │
│                                                                                  │
│  6. AI COPILOT (MOCK)                                                            │
│     4-stage pipeline designed. Keyword intent classification.                   │
│     ⚠️ All responses are templates. Qwen3:8b NOT wired.                          │
│                                                                                  │
│  7. DOCKER COMPOSE DEPLOYMENT                                                    │
│     8 services, one-command startup                                              │
│     ⚠️ No auth, no HTTPS, no production hardening                                │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  RESULTS (HONEST)                                                                │
│                                                                                  │
│  Metric                    │ Value                           │ Status           │
│  ────────────────────────────────────────────────────────────────────────────    │
│  Tests passing             │ 109 (dashboard focused)         │ ⚠️ Dashboard only │
│  Known test failures       │ 18 (env-dependent)              │ ⚠️ Pre-existing   │
│  Model coverage            │ 0% of model code tested        │ ❌ Need tests      │
│  API coverage              │ 0% of API code tested          │ ❌ Need tests      │
│  E2E pipeline (synthetic)  │ 17/17 stages pass              │ ✅ On synthetic    │
│  Docker compose            │ 8 services up                   │ ✅ Demo ready      │
│  Authentication            │ NONE                            │ ❌ Critical gap    │
│  Real data ingested        │ NONE                            │ ❌ Critical gap    │
│  LLM integration           │ NONE                            │ ❌ Critical gap    │
│  Best RMSE                 │ 4.53 (LSTM, on synthetic)       │ ⚠️ Meaningless    │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  PATH TO PRODUCTION                                                              │
│                                                                                  │
│  1. 🔴 Real data ingestion (NASA POWER / IMD / ISRO)                            │
│  2. 🔴 Wire LLM to copilot (Qwen3:8b)                                           │
│  3. 🔴 Authentication + HTTPS + rate limiting                                    │
│  4. 🟡 Add test coverage for models, APIs, RAG, copilot                         │
│  5. 🟡 Connect SHAP to model gradients                                           │
│  6. 🟡 Load testing                                                             │
│  7. 🟢 Scale from Karnataka to all India                                         │
│  8. 🟢 Train stubs (PatchTST, TimeMixer, iTransformer)                          │
│  9. 🟢 Mobile app, decision intelligence layer                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════════════════════════════╗
║  ISRO BAH 2026 — Challenge 5 · AI-Powered Digital Twin of India's Climate      ║
║  STATUS: PROOF-OF-CONCEPT · NOT PRODUCTION-READY · SYNTHETIC DATA              ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```
