#!/usr/bin/env bash
# Idempotent bootstrap for the Personal Finance AI dev environment.
# Safe to run repeatedly: it refreshes dependencies without duplicating state.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Ensuring Python venv tooling is available"
if ! python3 -m venv /tmp/.pfai-venv-probe >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv
fi
rm -rf /tmp/.pfai-venv-probe

echo "==> Installing backend dependencies"
cd "$ROOT/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
# Seed sample data only if the database is empty (seed() is a no-op otherwise).
python -m app.seed
deactivate

echo "==> Installing frontend dependencies"
cd "$ROOT/frontend"
npm install --no-audit --no-fund

echo "==> Install complete"
