.PHONY: help install test lint pipeline train dashboard docker up down demo clean

help:
	@echo "Climate Digital Twin — Make Commands"
	@echo ""
	@echo "  make install    — Install Python dependencies"
	@echo "  make test       — Run all tests"
	@echo "  make lint       — Run linter"
	@echo "  make pipeline   — Run data pipeline"
	@echo "  make train      — Train forecasting models"
	@echo "  make dashboard  — Launch dashboard locally"
	@echo "  make docker     — Build Docker images"
	@echo "  make up         — Start all services with Docker Compose"
	@echo "  make down       — Stop all services"
	@echo "  make demo       — Full demo walkthrough"
	@echo "  make clean      — Clean temporary files"

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check .

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
	@echo "Dashboard: http://localhost:8501"

down:
	docker compose down

demo:
	@bash deployment/scripts/demo.sh

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
