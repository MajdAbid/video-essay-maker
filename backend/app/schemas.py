from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from .utils.enums import JobStatus


class JobCreate(BaseModel):
    topic: str = Field(..., min_length=3, max_length=255)
    style: str = Field(..., min_length=3, max_length=255)
    length: int = Field(..., gt=30, description="Desired length in seconds")
    image_prompts: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional structured image prompt overrides."
    )


class JobPatch(BaseModel):
    script: Optional[str] = Field(None, description="Updated narration script text")
    transcript: Optional[str] = Field(
        None, description="Updated narration transcript for TTS."
    )
    image_prompts: Optional[Dict[str, Any]] = Field(
        default=None, description="Updated structured image prompts."
    )
    youtube_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Override YouTube research context."
    )


class JobResponse(BaseModel):
    id: str
    topic: str
    style: str
    length: int
    status: JobStatus
    script_status: JobStatus
    audio_status: JobStatus
    video_status: JobStatus
    script: Optional[str]
    transcript: Optional[str]
    image_prompts: Optional[Dict[str, Any]]
    review_score: Optional[float]
    generation_time: Optional[float]
    video_url: Optional[str]
    audio_path: Optional[str]
    frames_path: Optional[str]
    youtube_context: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    items: list[JobResponse]
