#!/bin/bash
# Production entrypoint for the AarogyaShield backend.
# Runs inside the container after all depends_on conditions are satisfied.
#
# Steps:
#   1. Wait for PostgreSQL to accept connections (belt-and-suspenders — Compose
#      already checked service_healthy, but pg_isready is fast and safe to repeat)
#   2. Start uvicorn (SQLAlchemy's create_all runs inside the lifespan hook)
set -euo pipefail

# ── 1. Wait for PostgreSQL ────────────────────────────────────────────────────
echo "[start.sh] Verifying PostgreSQL connection..."

MAX_RETRIES=30
RETRY_COUNT=0
until pg_isready \
        -h "${POSTGRES_HOST:-postgres}" \
        -p "${POSTGRES_PORT:-5432}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -q; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    echo "[start.sh] ERROR: PostgreSQL did not become ready after ${MAX_RETRIES} attempts. Exiting."
    exit 1
  fi
  echo "[start.sh] PostgreSQL not ready — attempt ${RETRY_COUNT}/${MAX_RETRIES}, retrying in 2s..."
  sleep 2
done

echo "[start.sh] PostgreSQL is ready."

# ── 2. Start uvicorn ──────────────────────────────────────────────────────────
# SQLAlchemy create_all() runs inside app.lifespan on startup — no separate
# migration step needed at this stage (Alembic migrations added in a future phase).
#
# --proxy-headers: trust X-Forwarded-For from nginx
# --workers: controlled by WORKERS env var (default 2 for containers with 1-2 vCPU)
WORKERS="${WORKERS:-2}"

echo "[start.sh] Starting uvicorn with ${WORKERS} worker(s)..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WORKERS}" \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --log-level "${LOG_LEVEL:-info}"
