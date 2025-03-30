#!/bin/sh
set -e  # exit on error

if [ "$ENV" = "prod" ]; then
  echo "Starting in production mode (gunicorn)..."
  exec gunicorn app.main:app \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
else
  echo "Starting in dev mode (uvicorn)..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi