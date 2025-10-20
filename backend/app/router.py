from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.exc import NoResultFound

from .schemas import JobCreate, JobListResponse, JobPatch, JobResponse
from .utils.config import get_settings
from .utils.enums import JobStatus
from .utils.security import verify_token


settings = get_settings()
router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate) -> JobResponse:
    # Lazy import to avoid importing DB at module import time
    from .utils.db import JobModel  # noqa: WPS433

    job = await JobModel.create(**payload.dict())
    from .tasks import generate_script  # noqa: WPS433

    generate_script.delay(job.id)
    return JobResponse.from_orm(job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(limit: int = 20) -> JobListResponse:
    from .utils.db import JobModel  # noqa: WPS433

    items = await JobModel.list(limit=limit)
    return JobListResponse(items=[JobResponse.from_orm(item) for item in items])


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    from .utils.db import JobModel  # noqa: WPS433

    job = await JobModel.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.from_orm(job)


@router.patch("/jobs/{job_id}", response_model=JobResponse)
async def edit_job(job_id: str, patch: JobPatch) -> JobResponse:
    from .utils.db import JobModel  # noqa: WPS433

    data = patch.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes provided")
    try:
        job = await JobModel.update(job_id, **data)
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    return JobResponse.from_orm(job)


@router.post("/jobs/{job_id}/rerender", status_code=status.HTTP_202_ACCEPTED)
async def rerender(job_id: str) -> dict[str, str]:
    from .utils.db import JobModel  # noqa: WPS433

    job = await JobModel.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    from .tasks import generate_script  # noqa: WPS433

    await JobModel.update(
        job_id,
        status=JobStatus.QUEUED,
        script_status=JobStatus.QUEUED,
        audio_status=JobStatus.NOT_REQUESTED,
        video_status=JobStatus.NOT_REQUESTED,
        audio_path=None,
        video_url=None,
        frames_path=None,
        transcript=None,
    )
    generate_script.delay(job.id)
    return {"message": "Script regeneration started"}


@router.post("/jobs/{job_id}/audio", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_audio(job_id: str, voice: str | None = None) -> JobResponse:
    from .utils.db import JobModel  # noqa: WPS433

    job = await JobModel.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.script_status != JobStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Script must be generated first")

    await JobModel.update(job_id, audio_status=JobStatus.QUEUED)
    from .tasks import generate_audio  # noqa: WPS433

    generate_audio.delay(job.id, voice)
    refreshed = await JobModel.get(job_id)
    return JobResponse.from_orm(refreshed)


@router.post("/jobs/{job_id}/video", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_video(job_id: str) -> JobResponse:
    if not settings.enable_image_generation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image generation disabled")

    from .utils.db import JobModel  # noqa: WPS433

    job = await JobModel.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.audio_status != JobStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio must be generated first")

    await JobModel.update(job_id, video_status=JobStatus.QUEUED)
    from .tasks import generate_video  # noqa: WPS433

    generate_video.delay(job.id)
    refreshed = await JobModel.get(job_id)
    return JobResponse.from_orm(refreshed)


@router.get(
    "/jobs/{job_id}/artifact/{artifact_type}",
    responses={200: {"content": {"text/plain": {}}}},
)
async def retrieve_artifact(job_id: str, artifact_type: str) -> Response:
    from .utils.db import JobModel  # noqa: WPS433

    job = await JobModel.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job_dir = settings.artifacts_root / job_id
    if artifact_type == "frames":
        image_file = job_dir / "image.png"
        if image_file.exists():
            return PlainTextResponse(image_file.name)
        frames_dir = job_dir / "frames"
        if not frames_dir.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frames not available")
        files = sorted(str(p.name) for p in frames_dir.glob("*.png"))
        return PlainTextResponse("\n".join(files))

    mapping = {
        "script": job_dir / "script.txt",
        "transcript": job_dir / "transcript.txt",
        "image": job_dir / "image.png",
        "audio": job_dir / "audio.wav",
        "video": job_dir / "final.mp4",
    }
    if artifact_type not in mapping:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact type")

    path = mapping[artifact_type]
    if artifact_type == "transcript" and not path.exists():
        if job.transcript:
            return PlainTextResponse(job.transcript)
    if artifact_type == "audio" and not path.exists():
        # Backwards compatibility for jobs generated before audio artifacts were copied to job root
        fallback = job.audio_path
        if fallback:
            fallback_path = Path(fallback)
            if fallback_path.exists():
                path = fallback_path

    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    media_type = "text/plain"
    if artifact_type == "audio":
        media_type = "audio/wav"
    elif artifact_type == "video":
        media_type = "video/mp4"
    elif artifact_type == "image":
        media_type = "image/png"

    return FileResponse(path, media_type=media_type, filename=path.name)
