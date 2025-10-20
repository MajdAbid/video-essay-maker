ARG BACKEND_IMAGE=backend:latest
FROM ${BACKEND_IMAGE}

WORKDIR /app

COPY worker/requirements.txt /tmp/worker-requirements.txt
RUN pip install -r /tmp/worker-requirements.txt && rm /tmp/worker-requirements.txt

ENV CELERY_LOG_LEVEL=INFO \
    CELERY_WORKER_CONCURRENCY=1

COPY backend/app ./app
COPY worker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]

