#!/usr/bin/env bash
set -euo pipefail

# Idempotent bootstrap for the world sugar dashboard.
# Regenerates the static payload from CSVs. No third-party packages are required.

cd "$(dirname "$0")/.."

python3 scripts/prepare_data.py

echo "Environment ready. Serve the dashboard with: python3 -m http.server 8000"
