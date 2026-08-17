#!/usr/bin/env bash
# Idempotent bootstrap for the AI-Assisted Personal Finance dev environment.
# Installs system deps (Python venv tooling, PostgreSQL + pgvector), sets up the
# database, and installs backend + frontend dependencies. Safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Ensuring system packages (python venv, PostgreSQL, pgvector)"
NEED_APT=0
python3 -m venv /tmp/.pfai-probe >/dev/null 2>&1 || NEED_APT=1
rm -rf /tmp/.pfai-probe
command -v psql >/dev/null 2>&1 || NEED_APT=1
if [ "$NEED_APT" = "1" ]; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv postgresql postgresql-contrib postgresql-16-pgvector
fi

echo "==> Starting PostgreSQL"
if ! pg_isready -q -h 127.0.0.1 -p 5432; then
  sudo pg_ctlcluster 16 main start
fi
for _ in $(seq 1 30); do
  pg_isready -q -h 127.0.0.1 -p 5432 && break
  sleep 1
done

echo "==> Ensuring database role, database, and pgvector extension"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='finance'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE ROLE finance LOGIN PASSWORD 'finance';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='finance'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE finance OWNER finance;"
sudo -u postgres psql -d finance -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null

echo "==> Installing backend dependencies"
cd "$ROOT/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
# Creates tables and seeds a demo user only if it doesn't already exist.
python -m app.seed
deactivate

echo "==> Installing frontend dependencies"
cd "$ROOT/frontend"
npm install --no-audit --no-fund

echo "==> Install complete"
