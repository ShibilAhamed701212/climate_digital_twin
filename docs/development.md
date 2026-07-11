# Development Guide

## Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install in editable mode
pip install -e ".[dev]"

# Verify installation
python -c "from runtime.runtime import AgentRuntime; print('Runtime OK')"
python -c "import climatedt; print('ClimateDT OK')"
```

## Project Conventions

### Code Style

- Python 3.11+, type annotations encouraged (not strictly enforced)
- 100 character line limit (configured in `pyproject.toml`)
- Ruff for linting: `ruff check backend/ climatedt/ copilot/ dashboard/`
- MyPy for type checking: `mypy runtime/ --ignore-missing-imports`
- Black for formatting: `black .`
- isort for import sorting: `isort .`

### Architecture Rules

Runtime code (`runtime/`) must never:
- Contain climate-specific terms (weather, rainfall, temperature, twin, forecast, etc.)
- Import from domain packages (`climatedt`, `copilot`, `models`, etc.)
- Reference domain-specific concepts

These rules are enforced by `runtime/test_architecture.py` using AST parsing and forbidden-term scanning.

### Testing

```bash
# Run all 2,266 tests
pytest tests/

# Run with coverage
pytest tests/ --cov

# Run specific test files
pytest tests/unit/dashboard/test_dashboard.py -v

# Run architecture tests
pytest runtime/test_architecture.py -v

# Run benchmarks
pytest runtime/benchmarks/ -v
```

- **2,266 tests** total (all passing)
- Tests are in `tests/` directory (dashboard tests, unit tests, integration tests)
- Coverage target: **80%** (currently at **23%** — work in progress)
- Framework: **pytest** with pytest-asyncio, pytest-cov
- 109 dashboard tests pass

**Note:** `models/` and `runtime/` packages are excluded from Windows coverage because torch C++ DLL crashes on this platform. Full coverage for these packages is achievable on Linux CI.

## Directory Structure (Key Packages)

```
├── backend/           FastAPI microservices (21 files)
├── climatedt/         Climate domain logic (31 files)
├── copilot/           Copilot agent system (39 files)
├── dashboard/         Streamlit dashboard (31 files)
│   ├── app.py         Entry point
│   ├── page_views/    10 dashboard pages (NOT pages/)
│   ├── services/      API client + synthetic fallback
│   ├── config/        Dashboard configuration
│   └── sidebar_nav.py Custom sidebar navigation
├── knowledge/         RAG pipeline (30 files)
├── models/            ML model definitions (29 files)
├── pipeline/          Data pipeline (21 files)
├── risk/              Risk engine (21 files)
├── runtime/           AI Runtime engine (90 files)
├── simulator/         Scenario simulator (62 files)
└── tests/             All tests (2,266 tests)
```

## How to Add a New Dashboard Page

1. Create a new file in `dashboard/page_views/` (NOT `dashboard/pages/`)
2. Follow the naming convention: `NN_page_name.py`
3. Use `render_sidebar_nav()` for navigation
4. Use `DashboardAPIClient` from `dashboard/services/api_client.py` for backend calls
5. The API client automatically falls back to synthetic data if services are unavailable

```python
import streamlit as st
from dashboard.services.api_client import DashboardAPIClient
from dashboard.components import render_sidebar_nav

st.set_page_config(page_title="My Page", layout="wide")
render_sidebar_nav()

api = DashboardAPIClient()
data = api.get_forecast("Bengaluru Urban", days=7)
# data will be synthetic if services are unavailable
st.write(data)
```

## How to Add a New ML Model

1. Add model architecture in `models/forecasting/` (or appropriate subdirectory)
2. Create training pipeline that can run on synthetic data
3. Create inference wrapper for model serving
4. Write tests in the corresponding `tests/` directory

```python
# models/forecasting/model.py
import torch.nn as nn

class MyModel(nn.Module):
    def __init__(self, input_dim=5, hidden_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, x):
        return self.net(x)
```

## How to Add a New Backend Service

1. Create a Dockerfile in `deployment/docker/` (e.g., `Dockerfile.my_service`)
2. Add service definition to `docker-compose.yml`
3. Create FastAPI app in `backend/services/`
4. Add route to API gateway in `backend/api/routers/`
5. Add health check endpoint
6. Update dashboard API client in `dashboard/services/api_client.py`

## Docker Development

```bash
# Build and start all services
docker compose up --build

# Start specific services
docker compose up api-gateway forecast-engine -d

# View logs
docker compose logs -f api-gateway

# Rebuild single service
docker compose build forecast-engine
```

## Known Limitations

- All data is **synthetic** — no real climate observations have been ingested
- ML models **trained on synthetic data only** — not production quality
- RAG FAISS index is **empty by default** — run `python -m knowledge.pipelines.index` to populate
- Copilot returns **mock responses** — no real LLM integration
- Dashboard Pages 08–10 are **100% mock** with no API calls
- Dashboard uses `page_views/` directory (not the standard `pages/`)
