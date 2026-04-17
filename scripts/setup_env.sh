#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

UV_CACHE_DIR=.uv-cache uv sync

echo
echo "Environment is ready."
echo "Activate with: source .venv/bin/activate"
