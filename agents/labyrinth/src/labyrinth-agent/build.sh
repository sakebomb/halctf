#!/usr/bin/env bash
# Build + save the Turing's Labyrinth agent as a docker archive for HalCTF upload.
# Usage: ./build.sh [version]   e.g. ./build.sh v1
set -euo pipefail

VER="${1:-v1}"
IMAGE="labyrinth-agent:latest"
OUT="../labyrinth-agent-${VER}.tar"

cd "$(dirname "$0")"

echo "=== Building ${IMAGE} ==="
docker build -t "${IMAGE}" .

echo "=== Saving to ${OUT} (docker save — NOT plain tar) ==="
docker save "${IMAGE}" > "${OUT}"

echo "=== Verifying tarball is a valid docker archive ==="
tar -tf "${OUT}" | grep -q manifest.json && echo "  manifest.json present: OK"

SIZE_MB=$(( $(stat -c%s "${OUT}") / 1024 / 1024 ))
echo "=== ${OUT} = ${SIZE_MB} MB (limit 2560 MB) ==="
if [ "${SIZE_MB}" -gt 2560 ]; then
  echo "  WARNING: exceeds 2560 MB tarball limit!" >&2
  exit 1
fi
echo "=== Done. Upload ${OUT} to the Turing's Labyrinth CTF. ==="
