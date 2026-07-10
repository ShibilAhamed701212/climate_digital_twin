# Climate Copilot Report

## Overview

The Climate Copilot is an AI-powered assistant for the India Climate Digital Twin. It accepts natural language queries, classifies intent, plans and executes tool calls, and generates conversational responses. It serves as the primary interface between users and the underlying climate data systems (forecasting, digital twin, risk assessment, scenario simulation, RAG knowledge base).

## Architecture

The Copilot follows a 4-step pipeline:

```
User Query → Intent Classification → Planning → Execution → Response Generation → Answer
```

### Pipeline Steps

1. **Intent Classification** (`copilot/agent/intent_agent.py`): Classifies the user query into one of 8 intents using keyword matching with confidence scoring
2. **Planning** (`copilot/planner/planner.py`): Maps the detected intent to a sequence of tool calls with extracted parameters
3. **Execution** (`copilot/workflows/executor.py`): Runs each tool call through the ToolRegistry, collecting results and tracking latency
4. **Response Generation** (`copilot/workflows/generator.py`): Formats tool results into a conversational response, optionally using the LLM for natural language generation

## Components

### Intent Classification (`IntentAgent`)

| Property | Value |
|----------|-------|
| Source | `copilot/agent/intent_agent.py` |
| Method | Keyword-based pattern matching |
| Confidence Formula | `base_weight * 100 * (1 - 0.5^match_count)` |
| Entities Extracted | Location (regex `in\s+...`), Days (regex `\d+\s*days?`) |
| Sub-intents | temperature/rainfall/general (forecast), heat/flood/drought/composite (risk) |

#### Supported Intents

| Intent | Keywords | Base Weight |
|--------|----------|-------------|
| FORECAST | forecast, weather, temperature, rainfall, rain, will it | 0.85 |
| TWIN_STATE | twin state, current state, current condition, status, what is the state | 0.80 |
| SCENARIO | scenario, what if, simulate, simulation, if temperature | 0.85 |
| RISK | risk, danger, hazard, heat risk, flood risk, drought risk, vulnerable | 0.85 |
| RAG_QUERY | explain, what is, tell me about, how does, why does, define, what causes | 0.75 |
| REPORT | report, summary, generate report, export, compile | 0.80 |
| GREETING | hello, hi, hey, greetings, good morning, good evening | 0.90 |
| UNKNOWN | — | 0.0 |

### Planning Agent

| Property | Value |
|----------|-------|
| Source | `copilot/planner/planner.py` |
| Strategy | Intent-to-plan mapping via method dispatch |
| Default Location | Karnataka |
| Default Days | 3 |

Each intent maps to a specific plan:

| Intent | Tool Call(s) | Parameters |
|--------|-------------|------------|
| FORECAST | `forecast_tool` | location, days |
| TWIN_STATE | `digital_twin_tool` | location |
| SCENARIO | `scenario_simulator` | location, scenario_type, value=2.0 |
| RISK | `risk_assessor` | location |
| RAG_QUERY | `rag_retriever` | query, top_k=3 |
| REPORT | `forecast_tool` + `risk_assessor` + `report_generator` | location, days=3 |

### Tool Registry

6 tools are registered in `copilot/tools/registry.py`:

| Tool | Class | Description | Fallback Data |
|------|-------|-------------|---------------|
| `forecast_tool` | `ForecastTool` | 1–7 day climate forecast | Synthetic forecast via MD5-seeded RNG |
| `digital_twin_tool` | `DigitalTwinTool` | Current twin state | Synthetic state via MD5-seeded RNG |
| `scenario_simulator` | `ScenarioSimulatorTool` | What-if scenario simulation | Synthetic deltas by scenario type |
| `risk_assessor` | `RiskAssessorTool` | Heat/flood/drought risk scores | Synthetic scores (10–80) via RNG |
| `rag_retriever` | `RAGRetrieverTool` | Semantic knowledge base search | Static fallback results |
| `report_generator` | `ReportGeneratorTool` | Structured climate report | Template-based fallback string |

All tools inherit from `BaseTool` with the contract:
- `run(**kwargs)` → `dict[str, Any]`
- `validate(**kwargs)` → `tuple[bool, str]`
- `describe()` → `dict` with name, description, parameters
- `health_check()` → `tuple[bool, str]`

Every tool implements a **fallback pattern**: if the remote service is unreachable (ConnectionError, Timeout, HTTPError), the tool returns synthetically generated data with `fallback: True`.

### LLM Client

| Property | Value |
|----------|-------|
| Source | `copilot/llm/ollama_client.py` |
| Model | `qwen3:8b` |
| Base URL | `http://localhost:11434` (configurable via `OLLAMA_HOST` env) |
| Temperature | 0.1 |
| Max Tokens | 1024 |
| Timeout | 30 seconds |
| Transport | HTTPX sync client |

The client supports:
- `generate(prompt, system_prompt)` — direct prompt → response
- `generate_with_prompt_file(prompt_path, **kwargs)` — loads prompt template, formats with `str.format()`, then generates
- `health_check()` — queries `/api/tags`, verifies the configured model is available

### Conversation Memory

| Property | Value |
|----------|-------|
| Source | `copilot/memory/conversation_memory.py` |
| Window Size | 10 turns |
| Expiration | 60 minutes (inactivity) |
| Storage | In-memory dict of conversation_id → list of ConversationTurn |
| Turn Limit | Configurable via `window_size` |
| History Access | `get_history()`, `get_recent_context(turns=5)` |

### Response Generator

| Property | Value |
|----------|-------|
| Source | `copilot/workflows/generator.py` |
| LLM Integration | Optional; falls back to template-based formatters |

Response formatting strategies per intent:
- **FORECAST**: Tabular day-by-day forecast with temp, rainfall, humidity
- **TWIN_STATE**: Current conditions summary
- **SCENARIO**: Temperature/rainfall deltas with description
- **RISK**: Heat/flood/drought/composite scores with category
- **RAG_QUERY**: Knowledge base result listing with scores
- **REPORT**: Combined report or template-based string
- **GREETING**: Static welcome message
- **UNKNOWN**: "I'm not sure" guidance message

### Orchestrator

| Property | Value |
|----------|-------|
| Source | `copilot/workflows/orchestrator.py` |
| Max Iterations | 5 |
| Intermediate Steps | Returned by default |

The orchestrator wires all components together:
1. Creates or retrieves conversation context
2. Classifies intent via `IntentAgent`
3. Creates plan via `PlanningAgent`
4. Executes plan via `Executor`
5. Generates response via `ResponseGenerator`
6. Records conversation turn in memory

## API Endpoints

### Climate Copilot API (`copilot/api/main.py`)

FastAPI application:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health including Ollama status and tool health |
| `/ask` | POST | Process a natural language query |
| `/conversation` | POST | Create a new conversation |
| `/conversation/{id}/history` | GET | Retrieve conversation history |
| `/conversations` | GET | List all conversations with turn counts |

### AskResponse Model

| Field | Type | Description |
|-------|------|-------------|
| answer | str | Generated response text |
| citations | list[str] | Source citations |
| intermediate_steps | list[dict] | Per-tool execution results |
| latency_ms | float | End-to-end processing time |
| intent | str | Classified intent type |

## Configuration

Loaded from `copilot/configs/copilot.yaml`:

```yaml
llm:
  primary_model: "qwen3:8b"
  temperature: 0.1
  max_tokens: 1024
  context_window: 8192

memory:
  window_size: 10
  expiration_minutes: 60

orchestration:
  max_iterations: 5
  return_intermediate_steps: true

enabled_tools:
  - forecast_tool
  - digital_twin_tool
  - scenario_simulator
  - risk_assessor
  - rag_retriever
  - report_generator

performance_targets:
  simple_query_ms: 2000
  forecast_ms: 5000
  simulation_ms: 8000
  report_ms: 10000
```

## Data Models

Defined in `copilot/models.py`:

| Model | Fields |
|-------|--------|
| IntentType | Enum: FORECAST, TWIN_STATE, SCENARIO, RISK, RAG_QUERY, REPORT, GREETING, UNKNOWN |
| IntentResult | intent, confidence, entities, raw_query, sub_intent |
| ToolCall | tool_name, parameters, description |
| Plan | intent, steps (list[ToolCall]), required_context |
| ToolResult | tool_name, success, data, error, execution_time_ms |
| ConversationTurn | query, intent, plan, results, response, latency_ms, citations |
| CopilotResponse | answer, citations, intermediate_steps, latency_ms, intent, error |
| CopilotContext | conversation_id, history, metadata |

## Clients

The tools communicate with backend services through HTTP clients in `copilot/clients/`:

| Client | Service | Endpoint | Timeout |
|--------|---------|----------|---------|
| `ForecastClient` | Forecast API | POST `/predict` | 5s |
| `TwinClient` | Digital Twin API | GET `/state/{location}` | 5s |
| `ScenarioClient` | Scenario API | POST `/simulate` | 5s |
| `RiskClient` | Risk API | POST `/assess` | 5s |
| `RAGClient` | RAG Knowledge API | POST `/search` | 5s |
| `ReportClient` | Report API | POST `/generate` | 5s |

## Performance Targets

| Query Type | Target Latency | Typical Latency |
|------------|---------------|-----------------|
| Simple (greeting, unknown) | 2000 ms | < 50 ms |
| Forecast | 5000 ms | < 100 ms (synthetic) |
| Simulation | 8000 ms | < 100 ms (synthetic) |
| Report | 10000 ms | < 200 ms (synthetic) |

## Known Limitations

1. **Keyword-based intent classification** — no LLM-based intent detection; pattern matching is brittle for ambiguous queries
2. **Synthetic fallback data** — when backend services are unavailable, tools return deterministic but fake data
3. **In-memory conversation storage** — no persistence across restarts
4. **No authentication** — API endpoints are open with no auth middleware
5. **Single LLM model** — only `qwen3:8b` is configured; no model fallback chain
6. **No streaming** — responses are generated in full before returning; no SSE or chunked output
