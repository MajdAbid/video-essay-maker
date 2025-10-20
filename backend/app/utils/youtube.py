from __future__ import annotations

import logging
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from ..integrations.youtube.client import YouTubeClient, save_context
from .config import get_settings

LOGGER = logging.getLogger(__name__)


@lru_cache()
def _client() -> YouTubeClient:
    settings = get_settings()
    return YouTubeClient(
        api_key=settings.youtube_api_key,
        client_secrets=settings.youtube_client_secrets,
        token_path=settings.youtube_token_file,
    )


def _empty_context(topic: str, status: str, message: str = "") -> Dict[str, Any]:
    payload = {
        "topic": topic,
        "status": status,
        "message": message,
        "summary": "",
        "results": [],
        "transcripts": [],
        "context_text": "",
        "error": message or "",
    }
    return payload


def gather_context(topic: str, limit: int = 5) -> Dict[str, Any]:
    settings = get_settings()
    client = _client()

    if not client.is_configured():
        LOGGER.info("YouTube integration not configured. Falling back to LLM-only script generation.")
        return _empty_context(topic, status="disabled", message="YouTube credentials not configured.")

    if not client.ensure_ready():
        LOGGER.warning("YouTube integration unavailable. Continuing without research data.")
        return _empty_context(topic, status="unavailable", message="YouTube authentication failed.")

    try:
        search_results = client.search_videos(topic, top_k=limit)
    except Exception as exc:  # pragma: no cover - network dependency
        LOGGER.warning("YouTube search failed: %s", exc)
        return _empty_context(topic, status="error", message=str(exc))

    transcript_entries: List[Dict[str, Any]] = []
    combined_segments: List[str] = []
    for result in search_results[: limit]:
        transcript_text = ""
        try:
            transcript_text = client.transcript_text(
                result.video_id,
                languages=settings.youtube_transcript_languages,
                max_chars=settings.youtube_transcript_char_limit,
            )
        except Exception as exc:  # pragma: no cover
            LOGGER.debug("Transcript download failed for %s: %s", result.video_id, exc)
        transcript_entries.append(
            {
                "video_id": result.video_id,
                "title": result.title,
                "channel": result.channel,
                "published_at": result.published_at,
                "transcript": transcript_text,
                "url": f"https://youtu.be/{result.video_id}",
            }
        )
        if transcript_text:
            combined_segments.append(f"[{result.title}] {transcript_text}")

    summary = YouTubeClient.summarize_results(search_results)
    context_text = "\n".join([summary, *combined_segments]) if combined_segments else summary

    return {
        "topic": topic,
        "status": "ok",
        "message": "",
        "error": "",
        "summary": summary,
        "results": [asdict(result) for result in search_results],
        "transcripts": transcript_entries,
        "context_text": context_text,
    }


def write_context(job_id: str, payload: Dict[str, Any], base_dir: Path) -> Path:
    artifact = base_dir / job_id / "youtube_context.json"
    save_context(payload, artifact)
    return artifact
