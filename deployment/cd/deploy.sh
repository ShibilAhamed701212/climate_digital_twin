#!/bin/bash
set -euo pipefail

echo "=== Climate Digital Twin — Deploy ==="
if [ -z "${DOCKER_USERNAME:-}" ] || [ -z "${DOCKER_PASSWORD:-}" ]; then
  echo "Error: DOCKER_USERNAME and DOCKER_PASSWORD must be set."
  exit 1
fi

echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
docker compose build
docker compose push
echo "Deploy complete."
