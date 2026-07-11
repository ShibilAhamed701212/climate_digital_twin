# Copilot Report

> **⚠️ Copilot returns MOCK responses. No real LLM integration.  
> Qwen3:8b declared but never wired. The 4-stage pipeline is stubbed.**

---

## Architecture

```
User Query
    │
    ▼
  Intent Classifier (keyword-based)
    │
    ├── "forecast" → FORECAST intent
    ├── "risk"     → RISK intent
    ├── "scenario" → SCENARIO intent
    ├── "explain"  → EXPLAIN intent
    ├── "twin"     → TWIN intent
    ├── "help"     → HELP intent
    ├── "greeting" → GREETING intent
    └── *          → UNKNOWN intent
    │
    ▼
  Planner (⚠️ stub — returns plan from template)
    │
    ▼
  Executor (dispatches to tools)
    │
    ├── get_forecast()     → Calls forecasting API
    ├── get_risk()         → Calls risk API
    ├── run_scenario()     → Calls scenario engine
    ├── get_twin_state()   → Calls twin API
    ├── get_rag_context()  → Calls RAG API
    └── get_help()         → Returns help text
    │
    ▼
  Generator (⚠️ MOCK — returns template response, NO LLM call)
    │
    ▼
  Response to user
```

---

## Intent Classification

| Intent | Keywords | Examples | Status |
|--------|----------|----------|--------|
| FORECAST | forecast, predict, weather, rain, temp | "What's the forecast for Kalaburagi?" | ✅ Working (keyword) |
| RISK | risk, hazard, danger, flood, drought | "What are the flood risks in Mysuru?" | ✅ Working (keyword) |
| SCENARIO | scenario, what-if, +2°C, warming | "What if temperature rises by 2°C?" | ✅ Working (keyword) |
| EXPLAIN | explain, why, reason, cause | "Why is heat risk high?" | ✅ Working (keyword) |
| TWIN | twin, state, current, status | "What's the current twin state?" | ✅ Working (keyword) |
| HELP | help, what can you do, commands | "What can you do?" | ✅ Working (keyword) |
| GREETING | hi, hello, hey, namaste | "Hello!" | ✅ Working (keyword) |
| UNKNOWN | — | "Tell me a joke" | ✅ Falls through |

---

## Tools

| Tool | Backend API | Description | Status |
|------|-------------|-------------|--------|
| `get_forecast(location, days)` | Forecasting API | Get weather forecast | ✅ Calls API |
| `get_risk(location)` | Risk API | Get risk assessment | ✅ Calls API |
| `run_scenario(scenario_id)` | Scenario Engine | Run what-if scenario | ✅ Calls API |
| `get_twin_state(location)` | Twin API | Get digital twin state | ✅ Calls API |
| `get_rag_context(query)` | RAG API | Retrieve knowledge | ✅ Calls API |
| `get_help()` | — | Return help text | ✅ Static |

---

## Conversation Memory

| Feature | Implementation | Status |
|---------|---------------|--------|
| Storage | In-memory dictionary | ✅ Working |
| Turn limit | 10 turns | ✅ Working |
| Expiry | 60 minutes | ✅ Working |
| Persistence | None | ⚠️ Lost on restart |

---

## API Endpoints

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/ask` | POST | Ask a question | ✅ Mock response |
| `/conversation` | GET | Get conversation history | ✅ Working |
| `/health` | GET | Service health | ✅ Working |

---

## Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| Intent classification | <1ms | Simple keyword match |
| Tool execution | ~200ms–2s | Depends on backend API |
| Response generation | <1ms | Mock (no LLM call) |
| Simple query total | <50ms | No backend API needed (greeting/help) |
| Forecast query total | <100ms | Includes API call + mock generation |

---

## Response Generation (The Mock)

```python
# ⚠️ This is the entire "generator" — no LLM involved
def generate_response(intent, context):
    templates = {
        "FORECAST": f"The {intent} for {context.get('location', 'unknown')} shows moderate conditions.",
        "RISK": f"Based on current data, the {intent} level is moderate.",
        # ... template-based fallbacks for all intents
    }
    return templates.get(intent, "I'm not sure how to help with that.")
```

---

## Limitations (Critical)

1. **NO real LLM integration.** Qwen3:8b is declared in docker-compose but never called.
2. **Template responses.** All answers are templates with placeholder substitutions.
3. **No conversation understanding.** Cannot follow up, clarify, or reason.
4. **No context-aware responses.** Each query is independent despite conversation memory.
5. **No error recovery.** Fails gracefully for known intents only.
6. **No streaming.** All responses are single-shot JSON.
7. **No evaluation.** Response quality never measured against ground truth.
