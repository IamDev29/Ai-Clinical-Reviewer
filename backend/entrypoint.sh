#!/bin/sh
set -e

echo "[*] Starting AI Clinical Document Reviewer Backend..."

# Run database migrations if RUN_MIGRATIONS is true or not explicitly disabled
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "[*] Applying database migrations via Alembic..."
    alembic upgrade head || echo "[!] Warning: Migration attempt finished with status $?"
fi

# Run seed script if SEED_SAMPLE_DATA is set to true
if [ "$SEED_SAMPLE_DATA" = "true" ]; then
    echo "[*] Seeding sample clinical reports..."
    python scripts/seed_reports.py || echo "[!] Warning: Seeding finished with status $?"
fi

# Port support for dynamic container environments (Render/Railway bind to $PORT)
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "[*] Launching Uvicorn server on ${HOST}:${PORT}..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
