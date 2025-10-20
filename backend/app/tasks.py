from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from celery import Celery

from .utils import imggen, llm, metrics, tts, video, youtube
from .utils.config import get_settings
from .utils.db import JobModel, JobStatus, init_db_sync

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "video_generator",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.celery_result_backend or settings.redis_url,
)
celery_app.conf.task_time_limit = 60 * 30
celery_app.conf.task_routes = {
    "backend.app.tasks.generate_script": {"queue": "pipeline"},
    "backend.app.tasks.generate_audio": {"queue": "audio"},
    "backend.app.tasks.generate_video": {"queue": "pipeline"},
}
celery_app.conf.task_default_queue = "pipeline"

try:
    init_db_sync()
except Exception as exc:  # noqa: BLE001
    logger.warning("Database initialization failed: %s", exc)

if settings.celery_audio_worker:
    try:
        tts._kokoro_service()
        logger.info("Kokoro TTS warmed up in audio worker process")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Kokoro warmup failed: %s", exc)


def _update_job(job, **changes):
    for key, value in changes.items():
        setattr(job, key, value)
    JobModel.save_sync(job)


@celery_app.task(name="backend.app.tasks.generate_script", bind=True)
def generate_script(self, job_id: str) -> str:
    job = JobModel.get_sync(job_id)
    if not job:
        logger.error("Job %s not found for script stage", job_id)
        return "missing"

    start_time = time.perf_counter()
    _update_job(
        job,
        status=JobStatus.PROCESSING,
        script_status=JobStatus.PROCESSING,
        started_at=datetime.utcnow(),
    )

    review_score = job.review_score
    youtube_context = job.youtube_context

    try:
        if settings.enable_youtube_research and (
            youtube_context is None or not youtube_context.get("results")
        ):
            youtube_context = youtube.gather_context(job.topic, settings.youtube_search_limit)
            job.youtube_context = youtube_context

        context_text = None
        if youtube_context and youtube_context.get("context_text"):
            context_text = youtube_context["context_text"]

        script = llm.generate_script(job.topic, job.style, job.length, context=context_text)
        transcript = llm.generate_transcript(script)
        review_score = llm.review_script(script)

        total_time = time.perf_counter() - start_time
        _update_job(
            job,
            script=script,
            transcript=transcript,
            review_score=review_score,
            status=JobStatus.COMPLETED,
            script_status=JobStatus.COMPLETED,
            finished_at=datetime.utcnow(),
            generation_time=total_time,
            youtube_context=youtube_context,
        )

        metrics.push(job_id, total_time, review_score, True)
        return "script"
    except Exception as exc:  # noqa: BLE001
        total_time = time.perf_counter() - start_time
        logger.exception("Script stage failed for job %s", job_id)
        _update_job(
            job,
            status=JobStatus.FAILED,
            script_status=JobStatus.FAILED,
            finished_at=datetime.utcnow(),
            generation_time=total_time,
        )
        metrics.push(job_id, total_time, review_score, False)
        raise self.retry(exc=exc, countdown=30, max_retries=1)


@celery_app.task(name="backend.app.tasks.generate_audio", bind=True)
def generate_audio(self, job_id: str, voice: Optional[str] = None) -> str:
    job = JobModel.get_sync(job_id)
    if not job:
        logger.error("Job %s not found for audio stage", job_id)
        return "missing"
    if not job.script:
        raise ValueError("Script must be generated before requesting audio")

    start_time = time.perf_counter()
    _update_job(job, audio_status=JobStatus.PROCESSING)

    try:
        narration_text = job.transcript or job.script
        if not job.transcript and job.script:
            logger.warning("Transcript missing for job %s, falling back to script for TTS", job_id)
        if not narration_text:
            raise ValueError("Transcript or script must be available for audio generation")
        temp_audio_path = tts.synthesize(job_id, narration_text, voice)
        job_dir = settings.artifacts_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        final_audio_path = job_dir / "audio.wav"
        if temp_audio_path != final_audio_path:
            shutil.copy2(temp_audio_path, final_audio_path)
        else:
            final_audio_path = temp_audio_path
        total_time = time.perf_counter() - start_time
        _update_job(
            job,
            audio_status=JobStatus.COMPLETED,
            audio_path=str(final_audio_path),
            generation_time=job.generation_time or total_time,
        )
        return "audio"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Audio stage failed for job %s", job_id)
        _update_job(job, audio_status=JobStatus.FAILED)
        raise self.retry(exc=exc, countdown=30, max_retries=1)


@celery_app.task(name="backend.app.tasks.generate_video", bind=True)
def generate_video(self, job_id: str) -> str:
    job = JobModel.get_sync(job_id)
    if not job:
        logger.error("Job %s not found for video stage", job_id)
        return "missing"
    if job.audio_status != JobStatus.COMPLETED:
        raise ValueError("Audio must be generated before video")
    if not settings.enable_image_generation:
        raise ValueError("Image generation is disabled on this deployment")

    start_time = time.perf_counter()
    _update_job(job, video_status=JobStatus.PROCESSING)

    try:
        prompts = job.image_prompts or llm.default_image_prompts(job.script or "")
        if isinstance(prompts, dict) and prompts:
            prompt_parts = next(iter(prompts.values()))
        else:
            prompt_parts = [job.script or ""]
        cover_image = imggen.render_cover_image(job_id, prompt_parts)
        audio_path = Path(job.audio_path) if job.audio_path else Path(tts.synthesize(job_id, job.script or ""))
        video_path = video.assemble_static(job_id, cover_image, audio_path)

        total_time = time.perf_counter() - start_time
        _update_job(
            job,
            video_status=JobStatus.COMPLETED,
            video_url=f"/artifacts/{job_id}/final.mp4",
            frames_path=str(cover_image),
            status=JobStatus.COMPLETED,
            generation_time=job.generation_time or total_time,
        )
        metrics.push(job_id, total_time, job.review_score, True)
        return "video"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Video stage failed for job %s", job_id)
        _update_job(job, video_status=JobStatus.FAILED)
        raise self.retry(exc=exc, countdown=30, max_retries=1)
