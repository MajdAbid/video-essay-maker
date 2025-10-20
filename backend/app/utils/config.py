from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, HttpUrl
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_SCRIPT_PROMPT = """You are a professional YouTube script writer. Create a {style} script about "{topic}". The narration should be approximately {minutes} minutes long (target length {length_seconds} seconds) and structured with short paragraphs. Include vivid scene descriptions and clear narration cues.{context_block}
"""

_DEFAULT_TRANSCRIPT_PROMPT = """You are preparing narration text that will be read verbatim by a text-to-speech system.

Rewrite the following YouTube video script as a flowing transcript with these rules:
- Do not include titles, section headings, numbers, or labels.
- Use only standard punctuation marks: period (.), comma (,), question mark (?), and exclamation mark (!).
- Preserve the meaning and tone, keeping language conversational and ready to be spoken aloud.
- Ensure sentences have natural spacing and cadence suitable for narration.

Script:
{script}

Transcript:"""

_DEFAULT_REVIEW_PROMPT = "You are a strict reviewer. Rate the script's coherence, length suitability, and style adherence between 0 and 100."


class Settings(BaseSettings):
    app_name: str = "Video Essay Maker"
    api_prefix: str = "/api/v1"
    api_token: str = Field("local-dev-token", env="API_TOKEN")

    database_url: str = Field(
        "sqlite+aiosqlite:///./jobs.db",
        env="DATABASE_URL",
        description="Async connection string used by FastAPI.",
    )
    sync_database_url: str = Field(
        "sqlite:///./jobs.db",
        env="SYNC_DATABASE_URL",
        description="Sync connection string used by Celery worker.",
    )

    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    celery_broker_url: Optional[str] = Field(None, env="CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(None, env="CELERY_RESULT_BACKEND")
    celery_audio_worker: bool = Field(False, env="CELERY_AUDIO_WORKER")

    artifacts_root: Path = Field(Path("data/jobs"), env="ARTIFACTS_ROOT")
    enable_image_generation: bool = Field(True, env="ENABLE_IMAGE_GENERATION")

    prometheus_pushgateway: Optional[str] = Field(
        "http://pushgateway:9091", env="PROMETHEUS_PUSHGATEWAY"
    )


    jwt_secret: str = Field("super-secret-key", env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_exp_minutes: int = Field(60 * 24, env="JWT_EXP_MINUTES")

    llm_model_name: str = Field(
        "openai/gpt-oss-20b",
        env="LLM_MODEL_NAME",
        description="Primary script generation model.",
    )
    llm_base_url: str = Field("http://localhost:1234/v1", env="LLM_BASE_URL")
    llm_api_key: Optional[str] = Field(None, env="LLM_API_KEY")
    llm_temperature: float = Field(0.7, env="LLM_TEMPERATURE")
    llm_top_p: float = Field(0.9, env="LLM_TOP_P")
    llm_script_prompt_file: Path = Field(
        Path("prompts/script_prompt.txt"),
        env="LLM_SCRIPT_PROMPT_FILE",
        description="Path to the main script prompt template.",
    )
    llm_transcript_prompt_file: Path = Field(
        Path("prompts/transcript_prompt.txt"),
        env="LLM_TRANSCRIPT_PROMPT_FILE",
        description="Path to the transcript prompt template.",
    )
    llm_reviewer_prompt_file: Path = Field(
        Path("prompts/reviewer_prompt.txt"),
        env="LLM_REVIEWER_PROMPT_FILE",
        description="Path to the reviewer prompt template.",
    )
    llm_reviewer_prompt: str = Field(_DEFAULT_REVIEW_PROMPT, env="LLM_REVIEWER_PROMPT")
    script_prompt_template: str = Field(_DEFAULT_SCRIPT_PROMPT, exclude=True)
    transcript_prompt_template: str = Field(_DEFAULT_TRANSCRIPT_PROMPT, exclude=True)
    reviewer_prompt_template: str = Field(_DEFAULT_REVIEW_PROMPT, exclude=True)

    tts_model_name: str = Field(
        "tts_models/en/vctk/vits",
        env="TTS_MODEL_NAME",
        description="Default TTS model identifier (ignored when using kokoro).",
    )
    tts_speed: float = Field(1.0, env="TTS_SPEED")

    diffusion_model_name: str = Field(
        "runwayml/stable-diffusion-v1-5",
        env="DIFFUSION_MODEL_NAME",
        description="Stable Diffusion model repository.",
    )

    ffmpeg_fps: int = Field(24, env="FFMPEG_FPS")
    frames_per_segment: int = Field(
        12,
        env="FRAMES_PER_SEGMENT",
        description="Number of frames generated per script paragraph.",
    )

    tts_provider: str = Field(
        "coqui",
        env="TTS_PROVIDER",
        description="TTS backend to use (coqui or kokoro).",
    )
    tts_voice: str = Field("Nova", env="TTS_VOICE", description="Default voice for Kokoro TTS.")

    enable_youtube_research: bool = Field(False, env="ENABLE_YOUTUBE_RESEARCH")
    youtube_api_key: Optional[str] = Field(None, env="YOUTUBE_API_KEY")
    youtube_client_secrets: Optional[Path] = Field(None, env="YOUTUBE_CLIENT_SECRETS")
    youtube_token_file: Path = Field(Path("youtube_token.json"), env="YOUTUBE_TOKEN_FILE")
    youtube_search_limit: int = Field(5, env="YOUTUBE_SEARCH_LIMIT")
    youtube_transcript_languages: List[str] = Field(
        default_factory=lambda: ["en", "en-US", "en-GB"],
        env="YOUTUBE_TRANSCRIPT_LANGUAGES",
    )
    youtube_transcript_char_limit: int = Field(6000, env="YOUTUBE_TRANSCRIPT_CHAR_LIMIT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("youtube_client_secrets", mode="before")
    def _expand_client_path(cls, value: Optional[str]) -> Optional[Path]:
        if value in (None, "", "None"):
            return None
        return Path(value).expanduser().resolve()

    @field_validator("youtube_transcript_languages", mode="before")
    def _normalize_langs(cls, value):
        if value is None:
            return ["en", "en-US", "en-GB"]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("youtube_token_file", mode="before")
    def _expand_token_path(cls, value: Optional[str]) -> Path:
        if not value:
            return Path("youtube_token.json").resolve()
        return Path(value).expanduser().resolve()

    @field_validator(
        "llm_script_prompt_file",
        "llm_transcript_prompt_file",
        "llm_reviewer_prompt_file",
        mode="before",
    )
    def _expand_prompt_path(cls, value: Optional[str]) -> Path:
        if value in (None, "", "None"):
            return Path("")
        return Path(value).expanduser().resolve()

    @field_validator("prometheus_pushgateway", mode="before")
    def _normalize_pushgateway(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("mlflow_tracking_uri", mode="before")
    def _normalize_mlflow_uri(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.artifacts_root = settings.artifacts_root.resolve()
    settings.artifacts_root.mkdir(parents=True, exist_ok=True)
    settings.script_prompt_template = _load_prompt(
        settings.llm_script_prompt_file, _DEFAULT_SCRIPT_PROMPT
    )
    settings.transcript_prompt_template = _load_prompt(
        settings.llm_transcript_prompt_file, _DEFAULT_TRANSCRIPT_PROMPT
    )
    settings.reviewer_prompt_template = _load_prompt(
        settings.llm_reviewer_prompt_file, _DEFAULT_REVIEW_PROMPT
    )
    settings.llm_reviewer_prompt = settings.reviewer_prompt_template
    return settings


def _load_prompt(path: Path, fallback: str) -> str:
    try:
        if path and str(path) and path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return content
    except Exception:
        pass
    return fallback.strip()
