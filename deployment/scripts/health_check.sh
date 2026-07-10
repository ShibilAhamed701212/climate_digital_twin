#!/bin/bash
set -euo pipefail

SERVICES=(
  "twin-state-mgr:8001"
  "scenario-engine:8002"
  "risk-engine:8003"
  "rag-service:8004"
  "copilot-agent:8005"
  "forecast-engine:8006"
  "report-service:8007"
  "fastapi-gateway:8000"
  "streamlit-dashboard:8501"
)

FAILED=0
for svc in "${SERVICES[@]}"; do
  NAME="${svc%%:*}"
  PORT="${svc##*:}"
  URL="http://localhost:${PORT}/health"
  if curl -sf "$URL" > /dev/null 2>&1; then
    echo "✅ $NAME ($URL)"
  else
    echo "❌ $NAME ($URL) - FAILED"
    FAILED=$((FAILED + 1))
  fi
done

if [ "$FAILED" -eq 0 ]; then
  echo ""
  echo "All services healthy!"
else
  echo ""
  echo "$FAILED service(s) unhealthy"
  exit 1
fi
