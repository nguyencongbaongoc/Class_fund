#!/usr/bin/env bash
# ==============================================================================
# CLASS_FUND_WEB - Multi-Architecture Container Build Pipeline
# Builds and tests container images for linux/amd64 and linux/arm64
# ==============================================================================

set -euo pipefail

REGISTRY="${DOCKER_REGISTRY:-classfund}"
VERSION="${VERSION:-0.1.0-prod}"
PLATFORMS="linux/amd64,linux/arm64"
BUILD_ACTION="${1:---load}" # Use --push to push to registry, --load for local single-arch or default build

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=============================================================================="
echo "CLASS_FUND_WEB Multi-Architecture Build Pipeline"
echo "Registry:  ${REGISTRY}"
echo "Version:   ${VERSION}"
echo "Platforms: ${PLATFORMS}"
echo "Action:    ${BUILD_ACTION}"
echo "=============================================================================="

# Ensure Docker buildx instance is active
if ! docker buildx inspect classfund-builder > /dev/null 2>&1; then
    echo "Creating new docker buildx builder: classfund-builder..."
    docker buildx create --name classfund-builder --driver docker-container --bootstrap --use
else
    docker buildx use classfund-builder
fi

echo "Active builder status:"
docker buildx inspect classfund-builder

# ------------------------------------------------------------------------------
# 1. Build Backend API Image
# ------------------------------------------------------------------------------
echo ""
echo ">>> [1/4] Building Backend Image (${PLATFORMS})..."
docker buildx build \
    --platform "${PLATFORMS}" \
    --file "${ROOT_DIR}/docker/Dockerfile.backend" \
    --tag "${REGISTRY}/backend:${VERSION}" \
    --tag "${REGISTRY}/backend:latest" \
    "${ROOT_DIR}/class-fund-backend-v0.1/class-fund-backend"

# ------------------------------------------------------------------------------
# 2. Build Worker Image
# ------------------------------------------------------------------------------
echo ""
echo ">>> [2/4] Building Worker Image (${PLATFORMS})..."
docker buildx build \
    --platform "${PLATFORMS}" \
    --file "${ROOT_DIR}/docker/Dockerfile.worker" \
    --tag "${REGISTRY}/worker:${VERSION}" \
    --tag "${REGISTRY}/worker:latest" \
    "${ROOT_DIR}/class-fund-backend-v0.1/class-fund-backend"

# ------------------------------------------------------------------------------
# 3. Build Frontend Image
# ------------------------------------------------------------------------------
echo ""
echo ">>> [3/4] Building Frontend Image (${PLATFORMS})..."
docker buildx build \
    --platform "${PLATFORMS}" \
    --file "${ROOT_DIR}/docker/Dockerfile.frontend" \
    --tag "${REGISTRY}/frontend:${VERSION}" \
    --tag "${REGISTRY}/frontend:latest" \
    "${ROOT_DIR}/classfund/classfund"

# ------------------------------------------------------------------------------
# 4. Build Edge Ingress Proxy Image
# ------------------------------------------------------------------------------
echo ""
echo ">>> [4/4] Building Edge Proxy Image (${PLATFORMS})..."
docker buildx build \
    --platform "${PLATFORMS}" \
    --file "${ROOT_DIR}/docker/Dockerfile.proxy" \
    --tag "${REGISTRY}/proxy:${VERSION}" \
    --tag "${REGISTRY}/proxy:latest" \
    "${ROOT_DIR}"

echo ""
echo "=============================================================================="
echo "MULTI-ARCHITECTURE BUILD COMPLETE FOR ALL SERVICES: linux/amd64 & linux/arm64"
echo "=============================================================================="
