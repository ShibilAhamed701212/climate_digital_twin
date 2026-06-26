#!/bin/bash
set -euo pipefail

echo "=== Climate Digital Twin — Startup ==="
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
  echo "Error: Docker is not installed."
  exit 1
fi

# Check for Docker Compose
if ! docker compose version &> /dev/null; then
  echo "Error: Docker Compose is not installed."
  exit 1
fi

echo "Building and starting all services..."
echo ""

docker compose up --build -d

echo ""
echo "Waiting for services to become healthy..."
sleep 10

# Run health check
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/health_check.sh"

echo ""
echo "Dashboard: http://localhost:8501"
echo "API Gateway: http://localhost:8000"
echo "Twin Core: http://localhost:8001"
echo "Scenario Engine: http://localhost:8002"
echo "Risk Engine: http://localhost:8003"
echo "RAG Service: http://localhost:8004"
echo "Copilot Agent: http://localhost:8005"
