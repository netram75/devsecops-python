#!/bin/sh
set -e

# RUN_MIGRATIONS=false lets a separate Job own migrations; by default every replica
# runs them and the advisory lock in alembic/env.py serialises the work.
python -m app.wait_for_db
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips='*' \
  "$@"
