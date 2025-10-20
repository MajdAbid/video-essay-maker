#!/usr/bin/env bash
set -euo pipefail

celery --app app.tasks.celery_app worker \
    --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
    --concurrency="${CELERY_WORKER_CONCURRENCY:-1}" \
    --queues="${CELERY_QUEUES:-pipeline,celery}"
