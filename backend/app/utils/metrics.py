from typing import Optional

import logging

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from .config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)
REGISTRY = CollectorRegistry()
GEN_TIME = Gauge(
    "video_generation_seconds",
    "Time taken to generate a video in seconds",
    ["job_id"],
    registry=REGISTRY,
)
REVIEW_SCORE = Gauge(
    "script_review_score",
    "LLM reviewer score (0-100)",
    ["job_id"],
    registry=REGISTRY,
)
SUCCESS_STATUS = Gauge(
    "video_generation_success",
    "1 if the pipeline completed successfully else 0",
    ["job_id"],
    registry=REGISTRY,
)


def push(job_id: str, gen_seconds: float, review_score: Optional[float], success: bool) -> None:
    GEN_TIME.labels(job_id=job_id).set(gen_seconds)
    if review_score is not None:
        REVIEW_SCORE.labels(job_id=job_id).set(review_score)
    SUCCESS_STATUS.labels(job_id=job_id).set(1 if success else 0)
    if not settings.prometheus_pushgateway:
        return
    try:
        push_to_gateway(settings.prometheus_pushgateway, job=job_id, registry=REGISTRY)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Prometheus push failed: %s", exc)
