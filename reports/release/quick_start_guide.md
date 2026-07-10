# Quick Start Guide — Climate Digital Twin

## Prerequisites

- **Docker** 20.10+ ([install](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.x+ (included with Docker Desktop)
- **Python** 3.10+ (optional, for local development only)

## 5-Step Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url> climate-digital-twin
cd climate-digital-twin
```

### Step 2: Configure Environment

```bash
cp deployment/configs/.env.example .env
```

The default configuration uses sensible defaults:
- All services run on standard ports (8000-8006, 8501, 11434)
- LLM model: `qwen3:8b` via Ollama
- Demo mode: `synthetic` (no external API dependencies)

### Step 3: Start All Services

```bash
docker compose up -d
```

This builds and starts **11 services** in the background:
- **8 application services:** twin-state-mgr, forecast-engine, scenario-engine, risk-engine, rag-service, copilot-agent, fastapi-gateway, streamlit-dashboard
- **LLM backend:** Ollama (Qwen3:8b)
- **Monitoring:** Prometheus, Grafana

**First-time setup** may take 5-10 minutes to:
- Download base Docker images (~2 GB total)
- Download Ollama model (Qwen3:8b, ~4.7 GB)
- Build service images with Python dependencies

### Step 4: Verify Health

```bash
python deployment/health/health_check.py
```

Expected output:
```
  ✅ twin-state-mgr
  ✅ scenario-engine
  ✅ risk-engine
  ✅ rag-service
  ✅ copilot-agent
  ✅ forecast-engine
  ✅ fastapi-gateway
  ✅ streamlit-dashboard

All services healthy!
```

Or use the shell script:
```bash
bash deployment/scripts/health_check.sh
```

### Step 5: Open the Dashboard

```
http://localhost:8501
```

Explore the **7-page dashboard**:
1. **Climate Overview** — Interactive map with current conditions
2. **Forecast Viewer** — 7-day predictions with confidence bands
3. **Digital Twin State** — Entity states, version history
4. **Scenario Simulator** — What-if analysis with 11 presets
5. **Climate Risk** — Heat/flood/drought scores with SHAP explanations
6. **Reports & Insights** — District summaries, data explorer
7. **Copilot Chat** — Natural-language climate intelligence

## What to Try Next

### Ask the Copilot

Use the API directly:
```bash
curl -X POST http://localhost:8005/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the flood risk for Bengaluru?"}'
```

### Get a Forecast

```bash
curl -X POST http://localhost:8006/forecast/predict \
  -H "Content-Type: application/json" \
  -d '{"horizon": 7, "model": "transformer"}'
```

### Search the Knowledge Base

```bash
curl -X POST http://localhost:8004/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Karnataka monsoon patterns", "top_k": 3}'
```

### Run a Scenario Simulation

```bash
curl -X POST http://localhost:8002/scenarios/simulate \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "temp_increase_2", "location_ids": ["KA-BLR-001"]}'
```

## Include Monitoring (Optional)

```bash
docker compose --profile monitoring up -d
```

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)

## Stop Everything

```bash
docker compose down
```

## One-Click Demo

```bash
bash deployment/scripts/demo.sh
```

See `deployment/docs/architecture.md` for full architecture details.
