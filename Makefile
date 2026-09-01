.PHONY: help install test lint format cov download-data pipeline train dashboard docker up down demo clean install-all validate

help:
	@echo "Climate Digital Twin — Make Commands"
	@echo ""
	@echo "  make install       — Install Python dependencies (dev)"
	@echo "  make install-all   — Install with all extras (dev + ollama)"
	@echo "  make test          — Run all tests"
	@echo "  make lint          — Run linter (ruff)"
	@echo "  make validate      — mypy DIE, OpenAPI contract, compose config"
	@echo "  make format        — Format code with ruff"
	@echo "  make cov           — Run tests with coverage"
	@echo "  make download-data — Download/generate required datasets"
	@echo "  make pipeline      — Run data pipeline"
	@echo "  make train         — Train forecasting models"
	@echo "  make dashboard     — Launch dashboard locally"
	@echo "  make docker        — Build Docker images"
	@echo "  make up-disaster   — Start climate stack + Disaster Intelligence profile"
	@echo "  make down          — Stop all services"
	@echo "  make demo          — Full demo walkthrough"
	@echo "  make clean         — Clean temporary files"

install:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all]"

test:
	pytest tests/ -v

lint:
	ruff check .

validate:
	python -m mypy disaster_intelligence --ignore-missing-imports
	python scripts/validate_openapi.py
	docker compose --profile disaster config --quiet

format:
	ruff format .

cov:
	pytest --cov=climatedt --cov=backend --cov=disaster_intelligence --cov=copilot --cov=risk --cov-report=xml --cov-report=term

download-data:
	python scripts/download_data.py --dataset all

pipeline:
	python pipeline/run_pipeline.py

train:
	python models/run_forecast.py

dashboard:
	streamlit run dashboard/app.py

docker:
	docker compose build

up:
	docker compose up --build -d
	@echo "Waiting for services..."
	@sleep 10
	@python deployment/health/health_check.py || true
	@echo ""
	@echo "Dashboard:        http://localhost:8501"
	@echo "API Gateway:      http://localhost:8000"

up-disaster:
	docker compose --profile disaster up --build -d
	@echo "Disaster Intelligence: http://localhost:8008"

down:
	docker compose down

demo:
	@bash deployment/scripts/demo.sh

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
