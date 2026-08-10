#!/bin/bash
# Local test script for HalCTF agent

set -e

IMAGE_NAME="halctf-agent"
TAG="latest"

echo "========================================"
echo "Testing HalCTF Agent Locally"
echo "========================================"

# Check if image exists
if ! docker images "${IMAGE_NAME}:${TAG}" | grep -q "${IMAGE_NAME}"; then
    echo "Error: Image ${IMAGE_NAME}:${TAG} not found"
    echo "Run ./build.sh first"
    exit 1
fi

echo "Running agent in test mode..."
echo ""

# Run with test environment variables
docker run --rm \
    -e HAL_USER_ID="test-user-12345" \
    -e USER_ID="test-user-12345" \
    -e OPENAI_BASE_URL="http://host.docker.internal:8000/v1" \
    -e MCP_ENDPOINT="http://host.docker.internal:8001" \
    -e BONUS_FLAG="flag{local_test_bonus}" \
    -e HAL_TARGET_IP="192.168.1.100" \
    -e HAL_TARGET_PORT="80" \
    --add-host=host.docker.internal:host-gateway \
    "${IMAGE_NAME}:${TAG}"

echo ""
echo "========================================"
echo "Test Complete!"
echo "========================================"
