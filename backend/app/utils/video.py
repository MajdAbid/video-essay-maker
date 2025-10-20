import logging
import subprocess
from pathlib import Path
from typing import Optional

from .config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


def assemble(job_id: str, frames_dir: Path, audio_path: Path, fps: Optional[int] = None) -> Path:
    output_dir = settings.artifacts_root / job_id / "temp"
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / "final.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps or settings.ffmpeg_fps),
        "-pattern_type",
        "glob",
        "-i",
        "*.png",
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(video_path),
    ]

    try:
        logger.info("Assembling video with ffmpeg (%s frames)", frames_dir)
        subprocess.run(cmd, cwd=frames_dir, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        logger.error("Video assembly failed: %s", exc.stderr)
        raise

    return video_path


def assemble_static(job_id: str, image_path: Path, audio_path: Path) -> Path:
    output_dir = settings.artifacts_root / job_id / "temp"
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / "final.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(video_path),
    ]

    try:
        logger.info("Assembling static video with ffmpeg (image=%s)", image_path)
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        logger.error("Video assembly failed: %s", exc.stderr)
        raise

    return video_path
