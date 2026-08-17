#!/usr/bin/env bash
# Per-boot startup: ensure PostgreSQL is running before the app terminals start.
# Idempotent and returns once the database is accepting connections.
set -euo pipefail

if ! pg_isready -q -h 127.0.0.1 -p 5432; then
  sudo pg_ctlcluster 16 main start || true
fi

for _ in $(seq 1 30); do
  if pg_isready -q -h 127.0.0.1 -p 5432; then
    echo "PostgreSQL is ready."
    exit 0
  fi
  sleep 1
done

echo "PostgreSQL did not become ready in time." >&2
exit 1
