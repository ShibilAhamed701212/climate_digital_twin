#!/bin/bash
set -euo pipefail

echo "=== Climate Digital Twin — Deploy ==="
echo ""
echo "Usage: DOCKER_REGISTRY=ghcr.io/myuser ./deploy.sh"
echo "  DOCKER_REGISTRY defaults to ghcr.io/\$GITHUB_REPOSITORY_OWNER"
echo ""

DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io/${GITHUB_REPOSITORY_OWNER:-climate-digital-twin}}"

GIT_SHA="${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo "latest")}"
GIT_BRANCH="${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")}"

export TAG="${GIT_BRANCH}-${GIT_SHA}"

if [ -z "${DOCKER_USERNAME:-}" ] || [ -z "${DOCKER_PASSWORD:-}" ]; then
  echo "Error: DOCKER_USERNAME and DOCKER_PASSWORD must be set."
  echo "In GitHub Actions, set these as secrets.DOCKER_USERNAME and secrets.DOCKER_PASSWORD."
  exit 1
fi

echo "Registry: $DOCKER_REGISTRY"
echo "Tag:      $TAG"
echo ""

echo "$DOCKER_PASSWORD" | docker login "$DOCKER_REGISTRY" -u "$DOCKER_USERNAME" --password-stdin

docker compose build
docker compose push

echo ""
echo "Deploy complete: ${DOCKER_REGISTRY}/climate-digital-twin:${TAG}"
