#!/bin/bash
set -euo pipefail

echo "=== Climate Digital Twin — Shutdown ==="
docker compose down
echo "All services stopped."
