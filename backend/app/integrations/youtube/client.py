"""
Utilities for interacting with the YouTube Data API and transcripts.

Adapted from the VideoMaker project to fit the FastAPI backend.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

LOGGER = logging.getLogger(__name__)

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


@dataclass(slots=True)
class YouTubeSearchResult:
    video_id: str
    title: str
    channel: str
    description: str
    published_at: str
    thumbnails: Dict[str, Any]


class YouTubeClient:
    """Wrapper around the YouTube Data API search and transcript helpers."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        client_secrets: Optional[Path] = None,
        token_path: Optional[Path] = None,
        scopes: Optional[Sequence[str]] = None,
        transcript_api: Optional[YouTubeTranscriptApi] = None,
    ) -> None:
        self.api_key = api_key
        self.client_secrets = client_secrets
        self.token_path = token_path or Path("youtube_token.json")
        self.scopes = tuple(scopes or YOUTUBE_SCOPES)
        self._service = None
        self._transcript_api = transcript_api or YouTubeTranscriptApi()
        self._auth_logged = False

    # ------------------------------------------------------------------ private

    def _authenticate(self) -> Any:
        if self.api_key:
            LOGGER.debug("Creating YouTube service with API key.")
            return build("youtube", "v3", developerKey=self.api_key)

        if not self.client_secrets or not self.client_secrets.exists():
            raise RuntimeError(
                "YouTube OAuth credentials are required. "
                "Set YOUTUBE_CLIENT_SECRETS pointing to the downloaded credentials.json."
            )

        creds: Optional[Credentials] = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secrets), self.scopes)
                creds = flow.run_local_server(port=0)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")

        return build("youtube", "v3", credentials=creds)

    def _get_service(self) -> Any:
        if self._service is None:
            self._service = self._authenticate()
        return self._service

    # ------------------------------------------------------------------ public

    @staticmethod
    def _prioritise_transcripts(transcripts: Sequence[Any], languages: Sequence[str]) -> Optional[Any]:
        if transcripts is None:
            return None
        options = list(transcripts)
        if not options:
            return None

        preferred = [lang.lower() for lang in languages]
        fallback = None
        for transcript in options:
            code = (getattr(transcript, "language_code", "") or "").lower()
            if code in preferred:
                return transcript
            if fallback is None and any(code.startswith(pref) for pref in preferred):
                fallback = transcript
        return fallback or options[0]

    def is_configured(self) -> bool:
        if self.api_key:
            return True
        if not self.client_secrets:
            return False
        return Path(self.client_secrets).exists()

    def ensure_ready(self) -> bool:
        if not self.is_configured():
            return False
        if self._service is not None:
            return True
        try:
            self._service = self._authenticate()
            if not self._auth_logged:
                LOGGER.info(
                    "YouTube API client authenticated using %s.",
                    "API key" if self.api_key else f"OAuth credentials at {self.client_secrets}",
                )
                self._auth_logged = True
            return True
        except Exception as exc:
            LOGGER.warning("YouTube authentication failed: %s", exc)
            return False

    def search_videos(self, query: str, *, top_k: int = 5) -> List[YouTubeSearchResult]:
        request = (
            self._get_service()
            .search()
            .list(part="snippet", q=query, type="video", maxResults=min(top_k, 50))
        )

        try:
            response = request.execute()
        except HttpError as exc:
            LOGGER.error("YouTube search failed: %s", exc)
            raise

        items = response.get("items", [])
        results: List[YouTubeSearchResult] = []
        for item in items:
            vid = item.get("id", {}).get("videoId")
            snippet = item.get("snippet") or {}
            if not vid:
                continue
            results.append(
                YouTubeSearchResult(
                    video_id=vid,
                    title=snippet.get("title", ""),
                    channel=snippet.get("channelTitle", ""),
                    description=snippet.get("description", ""),
                    published_at=snippet.get("publishedAt", ""),
                    thumbnails=snippet.get("thumbnails", {}),
                )
            )
        return results

    def fetch_transcript(
        self,
        video_id: str,
        *,
        languages: Optional[Sequence[str]] = None,
        raise_on_error: bool = False,
    ) -> Dict[str, Any]:
        preferred = tuple(languages or ("en", "en-US", "en-GB"))
        try:
            list_fn = (
                getattr(self._transcript_api, "list_transcripts", None)
                or getattr(self._transcript_api, "list", None)
            )
            if list_fn is None:
                raise AttributeError("YouTubeTranscriptApi instance missing list method")
            transcript_list = list(list_fn(video_id))
        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            if raise_on_error:
                raise
            LOGGER.debug("Transcript unavailable for %s: %s", video_id, exc)
            return {"video_id": video_id, "segments": [], "language": None, "is_generated": True}
        except Exception as exc:  # pragma: no cover - defensive guard
            if raise_on_error:
                raise
            LOGGER.warning("Transcript list failed for %s: %s", video_id, exc)
            return {"video_id": video_id, "segments": [], "language": None, "is_generated": True}

        transcript_obj = self._prioritise_transcripts(transcript_list, preferred)
        if transcript_obj is None:
            if raise_on_error:
                raise NoTranscriptFound(f"No transcripts available for {video_id}")
            LOGGER.debug("Transcript list empty for %s", video_id)
            return {"video_id": video_id, "segments": [], "language": None, "is_generated": True}

        language_code = getattr(transcript_obj, "language_code", None)
        try:
            segments = transcript_obj.fetch()
        except NoTranscriptFound:
            if raise_on_error:
                raise
            LOGGER.debug("Transcript language fallback failed for %s", video_id)
            segments = []
        except Exception as exc:  # pragma: no cover
            if raise_on_error:
                raise
            LOGGER.warning("Transcript fetch failed for %s: %s", video_id, exc)
            segments = []

        return {
            "video_id": video_id,
            "language": language_code,
            "is_generated": getattr(transcript_obj, "is_generated", False),
            "segments": segments,
        }

    def transcript_text(
        self,
        video_id: str,
        *,
        languages: Optional[Sequence[str]] = None,
        max_chars: int = 6_000,
    ) -> str:
        payload = self.fetch_transcript(video_id, languages=languages)
        sentences: List[str] = []
        for segment in payload.get("segments", []):
            text = segment.get("text")
            if text:
                sentences.append(text.strip())
        full_text = " ".join(sentences)
        if len(full_text) > max_chars:
            return full_text[: max_chars - 1].rstrip() + "…"
        return full_text

    @staticmethod
    def summarize_results(results: Iterable[YouTubeSearchResult]) -> str:
        lines = []
        for item in results:
            lines.append(
                f"- {item.title} (https://youtu.be/{item.video_id}) "
                f"by {item.channel} on {item.published_at[:10]}"
            )
        return "\n".join(lines)


def save_context(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
