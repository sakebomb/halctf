#!/bin/bash
# Build script for HalCTF agent

set -e

IMAGE_NAME="halctf-agent"
TAG="latest"
TARBALL="agent.tar"

echo "========================================"
echo "Building HalCTF Agent Docker Image"
echo "========================================"

# Build the image
echo "Building Docker image: ${IMAGE_NAME}:${TAG}"
docker build -t "${IMAGE_NAME}:${TAG}" .

# Get image size
IMAGE_SIZE=$(docker images "${IMAGE_NAME}:${TAG}" --format "{{.Size}}")
echo "Image size: ${IMAGE_SIZE}"

# Save as tarball
echo "Saving image as ${TARBALL}..."
docker save "${IMAGE_NAME}:${TAG}" > "${TARBALL}"

TARBALL_SIZE=$(du -h "${TARBALL}" | cut -f1)
echo "Tarball size: ${TARBALL_SIZE}"

echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo "Image: ${IMAGE_NAME}:${TAG}"
echo "Tarball: ${TARBALL}"
echo ""
echo "Next steps:"
echo "1. Test locally: ./test_local.sh"
echo "2. Upload to: https://halctf.aivillage.org"
echo "========================================"
