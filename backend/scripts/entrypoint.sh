#!/bin/sh
set -e

echo ">>> Running Alembic migrations..."
alembic upgrade heads

if [ "${SEED_ADMIN_ON_START:-false}" = "true" ]; then
    echo ">>> Seeding admin user (SEED_ADMIN_ON_START=true)..."
    python -m scripts.seed_admin || echo "Seed script returned non-zero (user may already exist) — continuing."
fi

echo ">>> Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
