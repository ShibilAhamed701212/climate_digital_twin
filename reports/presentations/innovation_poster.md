# Innovation Poster (Text Format)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║         AI-POWERED DIGITAL TWIN OF INDIA'S CLIMATE                             ║
║         ISRO BAH 2026 — Challenge 5 | June 2026                                 ║
╚══════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│  TEAM & PROJECT                                                                  │
│                                                                                  │
│  Project: AI-Powered Digital Twin of India's Climate                            │
│  Hackathon: ISRO BAH 2026 — Challenge 5: Digital Twin for Climate Resilience    │
│  Pilot Region: Karnataka, India (11.5-18.5°N, 74.0-78.5°E)                      │
│  Pilot Districts: Bengaluru Urban, Mysuru, Belagavi, Dakshina Kannada, Kalaburagi│
│  Version: 1.0.0 | Repository: climate-digital-twin                              │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  PROBLEM                                                                         │
│                                                                                  │
│  India loses 3-5% of GDP annually to climate-related disasters.                 │
│  60% of agriculture depends on monsoon rainfall.                                │
│  Climate data exists (IMD, ISRO, NASA) but is fragmented across agencies,       │
│  not localized to district level, and requires technical expertise to analyze.  │
│                                                                                  │
│  Key Question: Can we build a unified AI-powered system that:                   │
│    • Predicts rainfall and temperature at district scale                        │
│    • Simulates what-if climate scenarios                                        │
│    • Assesses heat, flood, and drought risk                                     │
│    • Answers natural language queries about climate conditions                   │
│    • Deploys with one command in any environment?                               │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  SOLUTION ARCHITECTURE                                                           │
│                                                                                  │
│  9-Microservice System — Docker Compose Orchestration                           │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                          STREAMLIT DASHBOARD                             │   │
│  │                  7 pages | Folium Maps | Plotly Charts                   │   │
│  └────────────────────────────────┬─────────────────────────────────────────┘   │
│                                   │                                              │
│  ┌────────────────────────────────▼──────────────────────────────────────────┐   │
│  │                          FASTAPI GATEWAY (8000)                           │   │
│  └──┬──────────┬──────────┬──────────┬──────────┬──────────┬─────────────────┘   │
│     │          │          │          │          │          │                     │
│     ▼          ▼          ▼          ▼          ▼          ▼                     │
│  ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐              │
│  │ TWIN │ │FORECAST│ │SCENARIO│ │  RISK  │ │  RAG   │ │ COPILOT  │              │
│  │8001  │ │ 8006   │ │ 8002   │ │ 8003   │ │ 8004   │ │ 8005     │              │
│  └──────┘ └────────┘ └────────┘ └────────┘ └────────┘ └─────┬────┘              │
│                                                              │                   │
│                                                   ┌──────────▼────────┐          │
│                                                   │  Ollama Qwen3:8b  │          │
│                                                   │     11434         │          │
│                                                   └───────────────────┘          │
│                                                                                  │
│  Monitoring: Prometheus (9090) + Grafana (3000)                                  │
│  CI/CD: GitHub Actions — Lint → Test (matrix 3.10/3.12) → Docker → Deploy       │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  DATA PIPELINE                                                                   │
│                                                                                  │
│  Source: NASA POWER API (PRECTOTCORR, T2M_MAX, T2M_MIN)                         │
│  Period: 1981-01-01 to 2023-12-31 (43 years)                                    │
│  Coverage: Karnataka — 48 grid cells at 0.5° resolution                         │
│                                                                                  │
│  Pipeline: Download → Validate → Clean → Feature Engineering → Export           │
│                                                                                  │
│  12 Engineered Features:                                                         │
│  • Temporal: Month, Week, Season, Monsoon, DayOfYear                            │
│  • Rolling: RollingRain7/30, RollingTemp7/30                                    │
│  • Trend: RainfallTrend, TempDiff, PriorRain7/30                                │
│                                                                                  │
│  Output: 628,200 processed rows | 70/15/15 temporal split                        │
│  Training: 439,740 rows | Validation: 94,230 | Testing: 94,230                   │
│  Quality: 0 missing values, all bounds validated                                 │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  KEY INNOVATIONS                                                                 │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗   │
│  ║  1. 7 MODEL ARCHITECTURES FOR ENSEMBLE CLIMATE FORECASTING               ║   │
│  ║     LSTM (RMSE 4.53), Transformer (RMSE 4.57), Baseline MLP (RMSE 4.59)  ║   │
│  ║     PatchTST, TimeMixer, iTransformer (stubs), Ensemble Meta-Learner      ║   │
│  ║     All trained models achieve R² = 0.87                                  ║   │
│  ║     PhysicsValidator: rainfall≥0, Tmin≤Tmax, temp bounds [-10,55]°C       ║   │
│  ╚═══════════════════════════════════════════════════════════════════════════╝   │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗   │
│  ║  2. DIGITAL TWIN WITH IMMUTABLE VERSIONING                                ║   │
│  ║     Append-only state manager, Parquet repository, EventBus pub/sub       ║   │
│  ║     4 state types: Current, Historical, Forecast, Scenario                ║   │
│  ╚═══════════════════════════════════════════════════════════════════════════╝   │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗   │
│  ║  3. SCENARIO SIMULATION ENGINE                                            ║   │
│  ║     5 scenario types, 11 presets, deterministic <3s execution             ║   │
│  ║     Temperature, Rainfall, Monsoon, Extreme Events, Combined scenarios    ║   │
│  ╚═══════════════════════════════════════════════════════════════════════════╝   │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗   │
│  ║  4. 4-COMPONENT RISK SCORING + SHAP EXPLAINABILITY                        ║   │
│  ║     Heat, Flood, Drought (0-100 each), Composite (weighted)               ║   │
│  ║     5 risk categories: Very Low → Severe                                  ║   │
│  ║     Deterministic SHAP with feature attribution + natural-language insights ║   │
│  ╚═══════════════════════════════════════════════════════════════════════════╝   │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗   │
│  ║  5. RAG KNOWLEDGE BASE OVER GOVERNMENT/ISRO/IMD DOCUMENTS                ║   │
│  ║     FAISS IndexFlatIP (384-dim), 15 sources, 30 chunks                    ║   │
│  ║     Recursive chunking at 700/120, semantic search <3ms                   ║   │
│  ║     5 format loaders: MD, TXT, CSV, JSON, PDF (stub)                      ║   │
│  ╚═══════════════════════════════════════════════════════════════════════════╝   │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗   │
│  ║  6. MULTI-AGENT AI COPILOT                                                ║   │
│  ║     4-step pipeline: Intent → Plan → Execute → Generate                   ║   │
│  ║     8 intent types, 6 tools, Qwen3:8b LLM via Ollama                      ║   │
│  ║     Conversation memory: 10 turns, 60min expiry                           ║   │
│  ╚═══════════════════════════════════════════════════════════════════════════╝   │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗   │
│  ║  7. FULL DOCKER COMPOSE DEPLOYMENT                                        ║   │
│  ║     11 services (8 app + 2 monitoring + Ollama)                           ║   │
│  ║     HEALTHCHECK on every service, Prometheus/Grafana monitoring           ║   │
│  ║     CI/CD pipelines, one-click startup, synthetic data fallback           ║   │
│  ╚═══════════════════════════════════════════════════════════════════════════╝   │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  RESULTS                                                                         │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐      │
│  │  METRIC                    │  VALUE                                    │      │
│  ├────────────────────────────────────────────────────────────────────────┤      │
│  │  Total Tests              │  656 (57 files)                            │      │
│  │  Unit Tests               │  ~620 passing                              │      │
│  │  Integration Tests        │  ~36 passing                               │      │
│  │  E2E Pipeline             │  17/17 stages (100%)                       │      │
│  │  Forecasting Models       │  7 architectures                           │      │
│  │  Best RMSE                │  4.53 (LSTM)                               │      │
│  │  R² Score                 │  0.87 (all models)                         │      │
│  │  Inference (fastest)      │  Transformer — 26.8 ms total               │      │
│  │  RAG Retrieval Rate       │  100% (8/8 queries)                        │      │
│  │  RAG Mean Latency         │  2.15 ms                                   │      │
│  │  Copilot Simple Query     │  < 50 ms                                   │      │
│  │  Docker Services          │  11                                        │      │
│  │  Dashboard Pages          │  7                                         │      │
│  │  Codebase Size            │  262 files, 17,354 LOC                     │      │
│  └────────────────────────────────────────────────────────────────────────┘      │
│                                                                                  │
│  Model Comparison:                                                                │
│                                                                                  │
│    RMSE:  Baseline 4.59 ─── LSTM 4.53 ─── Transformer 4.57                      │
│    R²:   All 0.87                                                                 │
│    Size: Baseline 94 KB ─── LSTM 802 KB ─── Transformer 2,847 KB                 │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  IMPACT                                                                          │
│                                                                                  │
│  🌾 Agriculture: 7-day forecasts for 60% of farmers dependent on monsoon         │
│  🏠 Disaster Preparedness: District-level risk scores (heat, flood, drought)    │
│  📊 Policy Planning: What-if scenario analysis for climate adaptation            │
│  🤖 Democratized Access: AI Copilot makes climate data accessible to all         │
│  🔓 Open Source: Freely available for any state or district to adapt             │
│                                                                                  │
│  Future Roadmap:                                                                  │
│  • National scale: Karnataka → All Indian states                                 │
│  • Train advanced models: PatchTST, TimeMixer, iTransformer                      │
│  • Real SHAP: Connect to model gradients                                         │
│  • Live data: Real-time IMD/INSAT feeds                                          │
│  • Mobile app: Farmer-facing extreme weather alerts                              │
│  • V2 Architecture: 11 services with data fusion, uncertainty, decision intel.   │
└──────────────────────────────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════════════════════════════╗
║  ISRO BAH 2026 — Challenge 5 · AI-Powered Digital Twin of India's Climate      ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```
