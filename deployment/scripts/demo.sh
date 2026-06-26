#!/bin/bash
set -euo pipefail

echo "╔══════════════════════════════════════════════════════╗"
echo "║   Climate Digital Twin — ISRO BAH 2026 Demo        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

echo "=== Step 1: Start all services ==="
docker compose up --build -d
echo ""

echo "=== Step 2: Wait for services to be ready ==="
sleep 15
echo ""

echo "=== Step 3: Verify health ==="
python deployment/health/health_check.py
echo ""

echo "=== Step 4: Demo walkthrough ==="
echo ""
echo "📊  Dashboard:     http://localhost:8501"
echo "🔗  API Gateway:   http://localhost:8000/docs"
echo ""
echo "1. Open the Dashboard to view climate overview"
echo "2. Navigate to Forecast Viewer for 7-day predictions"
echo "3. Try the Scenario Simulator with what-if analysis"
echo "4. Explore Climate Risk with SHAP explanations"
echo "5. Ask the Climate Copilot about weather, risks, or scenarios"
echo "6. Generate reports from the Reports & Insights page"
echo ""
echo "=== Demo Ready! ==="
