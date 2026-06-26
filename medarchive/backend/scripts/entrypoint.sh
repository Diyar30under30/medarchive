#!/usr/bin/env bash
# Docker container entrypoint: prepare schema + data, then serve the API.
# Each step is best-effort-logged; the server always comes up so /docs is reachable.
set -uo pipefail

echo "[entrypoint] DATABASE_URL=${DATABASE_URL:-sqlite (default)}"

# 1. Schema. Alembic owns it in Docker; create_all in lifespan is the fallback.
if [ -f "alembic.ini" ]; then
  echo "[entrypoint] applying migrations…"
  alembic upgrade head || echo "[entrypoint] WARN: alembic upgrade failed (lifespan create_all will cover dev)."
fi

# 2. Load the canonical reference directory (idempotent).
if [ "${AUTO_LOAD_REFERENCE:-false}" = "true" ]; then
  echo "[entrypoint] loading reference directory…"
  python -m scripts.load_reference || echo "[entrypoint] WARN: reference load skipped/failed."
fi

# 3. Optionally generate + ingest synthetic fixtures for an instant demo.
if [ "${AUTO_SEED_FIXTURES:-false}" = "true" ]; then
  echo "[entrypoint] seeding fixtures…"
  python -m scripts.generate_fixtures || echo "[entrypoint] WARN: fixture generation failed."
  python -m scripts.ingest ../data/incoming/sample_archive.zip || echo "[entrypoint] WARN: fixture ingest failed."
fi

# 4. Serve.
echo "[entrypoint] starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
