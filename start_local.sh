#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

export TWIN_STORE_DIR=data/twin_store
export GATEWAY_API_KEY_ENABLED=false
export GATEWAY_HOST=127.0.0.1
export PYTHONUNBUFFERED=1

LOGDIR=logs/local
mkdir -p "$LOGDIR"

start_service() {
  local name="$1" module="$2" port="$3"
  shift 3
  local extra_env=("$@")
  echo "[START] $name on :$port"
  (
    for kv in "${extra_env[@]}"; do export "$kv"; done
    exec python -m uvicorn "$module" --host 127.0.0.1 --port "$port" --log-level info
  ) > "$LOGDIR/$name.log" 2>&1 &
  echo "$!" > "$LOGDIR/$name.pid"
  echo "  PID=$(cat "$LOGDIR/$name.pid")"
}

# 1. Twin State Manager
start_service "twin" "simulator.api.main:app" 8001

# 2. Scenario Engine
start_service "scenario" "simulator.scenarios.api:app" 8002

# 3. Risk Engine
start_service "risk" "risk.api.main:app" 8003

# 4. RAG Knowledge Service
start_service "rag" "knowledge.api.main:app" 8004

# 5. Copilot Agent
start_service "copilot" "copilot.api.main:app" 8005

# 6. Forecast Engine
start_service "forecast" "backend.services.forecast.main:app" 8006

# 7. Report Service
start_service "report" "backend.api.report:app" 8007

# 8. API Gateway (depends on others)
start_service "gateway" "backend.api.main:app" 8000 \
  "TWIN_ENGINE_URL=http://127.0.0.1:8001" \
  "FORECAST_ENGINE_URL=http://127.0.0.1:8006" \
  "DISASTER_ENGINE_URL=http://127.0.0.1:8008"

# 9. Dashboard
echo "[START] dashboard on :8501"
python -m streamlit run dashboard/app.py \
  --server.port 8501 \
  --server.address 127.0.0.1 \
  --server.headless true \
  --browser.gatherUsageStats false \
  > "$LOGDIR/dashboard.log" 2>&1 &
echo "$!" > "$LOGDIR/dashboard.pid"
echo "  PID=$(cat "$LOGDIR/dashboard.pid")"

echo ""
echo "==========================================="
echo " All 9 services launched on localhost"
echo " Logs: $LOGDIR/"
echo "==========================================="
echo ""
echo " Waiting 5s for startup..."
sleep 5

echo ""
echo "=== Health Check ==="
for svc in "gateway:8000:/health/live" \
           "twin:8001:/health" \
           "scenario:8002:/health" \
           "risk:8003:/health" \
           "rag:8004:/health" \
           "copilot:8005:/health/live" \
           "forecast:8006:/health" \
           "report:8007:/health"; do
  IFS=: read name port path <<< "$svc"
  status=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port$path" 2>/dev/null || echo "000")
  if [ "$status" = "200" ]; then
    printf "  [OK]   %-12s :%s\n" "$name" "$port"
  else
    printf "  [FAIL] %-12s :%s (HTTP %s)\n" "$name" "$port" "$status"
  fi
done

# Dashboard
status=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8501" 2>/dev/null || echo "000")
if [ "$status" = "200" ]; then
  printf "  [OK]   %-12s :8501\n" "dashboard"
else
  printf "  [FAIL] %-12s :8501 (HTTP %s)\n" "dashboard" "$status"
fi

echo ""
echo "Dashboard:  http://127.0.0.1:8501"
echo "API Docs:   http://127.0.0.1:8000/docs"
echo ""
