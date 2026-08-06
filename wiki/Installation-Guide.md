# Installation Guide

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required |
| Docker & Docker Compose | Latest | For containerized deployment |
| Git | Latest | For cloning the repository |
| RAM | 4 GB minimum | 8 GB+ recommended for full stack with Ollama |
| Disk | 2 GB minimum | Plus space for data and model checkpoints |

## Installation Methods

### Method 1: Local Development Setup

```bash
# Clone the repository
git clone https://github.com/ShibilAhamed701212/climate_digital_twin.git
cd climate_digital_twin

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# Install with development dependencies
pip install -e ".[dev]"

# (Optional) Install with Ollama support for AI Copilot
pip install -e ".[all]"

# Copy and configure environment
cp .env.example .env
```

### Method 2: Docker Compose (Recommended for Full Stack)

```bash
# Clone and enter the project
git clone https://github.com/ShibilAhamed701212/climate_digital_twin.git
cd climate_digital_twin

# Copy environment configuration
cp .env.example .env

# Build and start all 10 services
docker compose up --build -d

# Verify services are running
docker compose ps
```

### Method 3: Make Commands

```bash
# Install dependencies
make install

# Install with all extras (dev + ollama)
make install-all
```

## Post-Installation Setup

### 1. Seed Sample Data

```bash
# Populate twin state with sample climate data
python scripts/seed_twin_data.py

# Generate sample forecast data
python scripts/seed_forecast_data.py
```

### 2. Index Knowledge Base

```bash
# Index climate documents into the FAISS vector store
python scripts/index_knowledge_base.py
```

### 3. Start Services

**Local development (individual services):**

```bash
# Start the API gateway
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# Start the dashboard (separate terminal)
streamlit run dashboard/app.py
```

**Windows (all services via script):**

```powershell
.\scripts\start_local_services.ps1
```

**Docker (all services):**

```bash
make up
```

### 4. Verify Installation

| Service | URL | Expected |
|---|---|---|
| Dashboard | http://localhost:8501 | Streamlit UI loads |
| API Gateway | http://localhost:8000 | JSON root response |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Health Check | http://localhost:8000/health | `{"status": "healthy"}` |

## Running Tests

```bash
# Full test suite with coverage
make test

# Or directly
pytest tests/ -v

# Linting
make lint
```

## Troubleshooting

| Issue | Solution |
|---|---|
| `torch` import fails on Windows | Install PyTorch separately: `pip install torch --index-url https://download.pytorch.org/whl/cpu` |
| Port already in use | Change ports in `.env` file |
| Ollama service unhealthy | Ensure Ollama is installed and the model is pulled: `ollama pull qwen3:4b` |
| FAISS import error | Install `faiss-cpu`: `pip install faiss-cpu` |
