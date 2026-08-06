# AI Copilot Assistant

## Overview

The **AI Copilot** (`copilot/`) provides an interactive conversational interface integrated directly into the Climate Digital Twin platform. Users can query climate states, request forecasts, run scenario simulations, check risk assessments, or search the knowledge base using natural language.

---

## Agent Architecture & Workflow

```
User Query ("What is the flood risk in Mysuru next week?")
                       │
                       ▼
            Intent Classifier Agent
                       │
                       ▼
                Query Planner
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Tool Execution      RAG Context Retrieval
     (Risk/Forecast API)  (FAISS Vector Store)
             └─────────┬─────────┘
                       ▼
              Response Generator
                       │
                       ▼
          LLM Inference (Ollama Qwen 3)
                       │
                       ▼
               Final Assistant Answer
```

---

## Copilot Tool Suite (`copilot/tools/`)

The agent dynamically selects from 7 specialized domain tools:

| Tool | Module | Functionality |
|---|---|---|
| `ForecastTool` | `forecast_tool.py` | Fetches multi-model weather forecasts for any location |
| `RiskAssessorTool` | `risk_tool.py` | Queries risk scores (Heat, Flood, Drought, Composite) |
| `ScenarioSimulatorTool` | `scenario_tool.py` | Invokes what-if climate simulations |
| `DigitalTwinTool` | `twin_tool.py` | Queries active digital twin state and history |
| `RAGRetrieverTool` | `rag_tool.py` | Searches domain documents for context |
| `ReportGeneratorTool` | `report_tool.py` | Composes structured markdown climate reports |
| `ToolRegistry` | `registry.py` | Manages tool registration and execution routing |

---

## Configuration & LLM Backend

- **Ollama Integration**: Runs locally via `OllamaClient` (`copilot/llm/ollama_client.py`). Default model: `qwen3:4b`.
- **System Prompts (`copilot/prompts/`)**: Engineered prompt templates for intent classification, query decomposition, and factual climate response generation.
- **Conversation Memory (`copilot/memory/`)**: Maintains multi-turn context per session.

---

## Running the Copilot Service

The Copilot runs as an independent microservice on port `8005`:

```bash
# Docker Compose
docker compose up copilot-agent

# Or launch as standalone service
python -m copilot.api.copilot_api
```

In the dashboard, navigate to **AI Copilot** (`07_copilot_chat.py`) to interact with the chat interface.
