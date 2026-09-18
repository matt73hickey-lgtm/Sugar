#!/usr/bin/env bash
set -euo pipefail

# Idempotent bootstrap for the agricultural-commodity data-analysis environment.
# Safe to re-run: it only installs what is missing and reuses the existing venv.

cd "$(dirname "$0")/.."

# python venv support is not part of the base image; install it once if absent.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3.12-venv
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo "Environment ready. Activate with: source .venv/bin/activate"
