# Project Timeline

> **6-week development sprint: May–July 2026**  
> From empty repository to hackathon submission.

---

## Timeline Overview

```
May 2026                    June 2026                        July 2026
├──┬──┬──┬──┬──┬──┬──┬──┬──┼──┬──┬──┬──┬──┬──┬──┬──┬──┬──┼──┬──┬──┬──┬──┬──┬──┬──┤
   ██  ██  ██  ██  ██  ██    ██  ██  ██  ██  ██  ██    ██  ██  ██  ██
   W1          W2          W3          W4          W5          W6
```

**Week 1 (May 18–24):** Scaffold + Synthetic Data  
**Week 2 (May 25–31):** Models + Training Pipeline  
**Week 3 (Jun 1–7):** Digital Twin + Scenarios  
**Week 4 (Jun 8–14):** Risk + RAG  
**Week 5 (Jun 15–21):** Copilot + Dashboard  
**Week 6 (Jun 22–Jul 11):** Docker + Reports + Polish

---

## Detailed Milestones

### Week 1: Scaffold + Synthetic Data
| Day | Task | Outcome |
|-----|------|---------|
| Mon | Project scaffold, directory structure | Repo initialized |
| Tue | Config files (YAML schema) | 15 districts configured |
| Wed | Synthetic data generator | `np.random.seed(42)` pipeline |
| Thu | Data validation + feature engineering | 12 engineered features |
| Fri | Parquet export + data splits | 628,200 synthetic rows |
| Sat | Basic API structure | FastAPI skeleton |
| Sun | Documentation setup | Report directory structure |

### Week 2: Models + Training Pipeline
| Day | Task | Outcome |
|-----|------|---------|
| Mon | Baseline MLP model | Implemented + trained on synthetic |
| Tue | LSTM model | Implemented + trained on synthetic |
| Wed | Transformer model | Implemented + trained on synthetic |
| Thu | PatchTST, TimeMixer, iTransformer stubs | Class definitions only |
| Fri | Ensemble wrapper | Ridge regression (not trained) |
| Sat | Training pipeline (loader, engine, eval) | Full pipeline on synthetic |
| Sun | PhysicsValidator | Basic constraint enforcement |

### Week 3: Digital Twin + Scenarios
| Day | Task | Outcome |
|-----|------|---------|
| Mon | ClimateEntity dataclass | Immutable + validated |
| Tue | StateManager (append-only versioning) | Version chain working |
| Wed | EventBus (pub/sub) | 5 event types |
| Thu | ParquetRepository | Per-location storage |
| Fri | Scenario types + presets | 5 types, 11 presets |
| Sat | Deterministic simulator | <3s execution |
| Sun | Scenario API + integration | Endpoints working |

### Week 4: Risk + RAG
| Day | Task | Outcome |
|-----|------|---------|
| Mon | Heat risk module | Scoring formula |
| Tue | Flood risk module | Scoring formula |
| Wed | Drought risk module | Scoring formula |
| Thu | Composite + configurable weights | risk.yaml |
| Fri | FAISS index + embedding pipeline | IndexFlatIP |
| Sat | Document loading + chunking | 15 docs, ~30 chunks |
| Sun | RAG API + endpoint | CRUD endpoints |

### Week 5: Copilot + Dashboard
| Day | Task | Outcome |
|-----|------|---------|
| Mon | Intent classifier (keyword) | 8 intents |
| Tue | Tool dispatch + executor | 6 tools |
| Wed | Response generator (mock) | Template-based |
| Thu | Conversation memory | 10 turns, 60min expiry |
| Fri | Dashboard pages 1–5 | Home, Forecast, Twin, Scenario, Risk |
| Sat | Dashboard pages 6–10 | Maps, About + 3 mock pages |
| Sun | Dashboard-API integration | Synthetic data flow |

### Week 6: Docker + Reports + Polish
| Day | Task | Outcome |
|-----|------|---------|
| Mon | Dockerfiles (8 services) | All containerized |
| Tue | docker-compose.yml | Orchestration working |
| Wed | Nginx gateway + health checks | Reverse proxy |
| Thu | Report writing (57 files) | Documentation |
| Fri | Report audit — inflated claims found | Correction begun |
| Sat–Sun | Honesty rewrite | All reports corrected |

---

## Key Dates

| Date | Milestone |
|------|-----------|
| May 18, 2026 | Project start |
| May 24, 2026 | First synthetic data generated |
| Jun 7, 2026 | Digital twin core complete |
| Jun 14, 2026 | Risk + RAG pipeline complete |
| Jun 21, 2026 | Dashboard + Copilot MVP |
| Jun 28, 2026 | Docker Compose working |
| Jul 11, 2026 | Reports audited + corrected |

---

## What Took Longer Than Expected

| Task | Expected | Actual | Reason |
|------|----------|--------|--------|
| Docker setup | 1 day | 3 days | Dependency chains, port conflicts |
| LLM integration | 2 days | **Not done** | Ollama 8GB download, never completed |
| Real data integration | 3 days | **Not done** | API key delays, never circled back |
| Dashboard polish | 3 days | 5 days | Plotly + Folium learning curve |
| Report writing | 1 day | 3 days | 57 files, inflated claims discovered |

## What Took Less Time Than Expected

| Task | Expected | Actual | Reason |
|------|----------|--------|--------|
| Synthetic data generator | 2 days | 4 hours | Simpler than expected |
| StateManager versioning | 2 days | 1 day | Clean dataclass design |
| Risk scoring formulas | 3 days | 1 day | Straightforward weighted sums |
