#!/usr/bin/env bash
# Build + save a HAL-format CTF agent as a docker archive for upload.
# Usage: ./build.sh <image-name> [version]   e.g. ./build.sh rogue-agent v1
set -euo pipefail

NAME="${1:?usage: ./build.sh <image-name> [version]}"
VER="${2:-v1}"
IMAGE="${NAME}:${VER}"
OUT="../${NAME}-${VER}.tar"

cd "$(dirname "$0")"

echo "=== Building ${IMAGE} ==="
docker build -t "${IMAGE}" .

echo "=== Saving to ${OUT} (docker save — plain .tar, NOT gzipped) ==="
docker save "${IMAGE}" > "${OUT}"

echo "=== Verifying tarball is a valid docker archive ==="
tar -tf "${OUT}" | grep -q manifest.json && echo "  manifest.json present: OK"

SIZE_MB=$(( $(stat -c%s "${OUT}") / 1024 / 1024 ))
echo "=== ${OUT} = ${SIZE_MB} MB ==="

echo "=== Local dry-run gate check ==="
docker run --rm -e HAL_DRY_RUN=1 -e HAL_USER_ID=localtest "${IMAGE}" \
  | grep -E "USER ID|Verification PASSED" || echo "  WARNING: dry-run gate output missing!"

echo "=== Done. Upload ${OUT}. ==="
