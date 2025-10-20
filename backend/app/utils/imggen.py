import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List

from PIL import Image, ImageDraw, ImageFont

from .config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


def _merge_prompt(parts: Iterable[str]) -> str:
    return " ".join(part.strip() for part in parts if part)


@lru_cache()
def _diffusion_pipeline():
    try:
        from diffusers import StableDiffusionPipeline
        import torch

        model = settings.diffusion_model_name
        logger.info("Loading diffusion model %s", model)
        pipe = StableDiffusionPipeline.from_pretrained(
            model,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
        return pipe
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to load Stable Diffusion pipeline (%s). Placeholder images will be used.",
            exc,
        )
        return None


def _placeholder_image(text: str, path: Path) -> None:
    image = Image.new("RGB", (1280, 720), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.multiline_text((40, 40), text[:512], fill=(255, 255, 255), font=font, spacing=4)
    image.save(path)


def render_cover_image(job_id: str, prompt_parts: List[str]) -> Path:
    """Generate a single cover image for the video background."""
    temp_dir = settings.artifacts_root / job_id / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    image_path = temp_dir / "cover.png"

    prompt = _merge_prompt(prompt_parts)
    pipeline = _diffusion_pipeline()

    if pipeline:
        try:
            result = pipeline(prompt, num_inference_steps=35, guidance_scale=7.5)
            result.images[0].save(image_path)
            return image_path
        except Exception as exc:  # noqa: BLE001
            logger.error("Cover image generation failed: %s", exc)

    _placeholder_image(prompt, image_path)
    return image_path


def render_frames(job_id: str, prompts: Dict[str, List[str]]) -> Path:
    frames_dir = settings.artifacts_root / job_id / "temp" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    pipeline = _diffusion_pipeline()

    for idx, (scene, parts) in enumerate(prompts.items()):
        prompt = _merge_prompt(parts)
        frame_path = frames_dir / f"{idx:04d}_{scene}.png"
        if pipeline:
            try:
                result = pipeline(prompt, num_inference_steps=35, guidance_scale=7.5)
                result.images[0].save(frame_path)
            except Exception as exc:  # noqa: BLE001
                logger.error("Image generation failed: %s", exc)
                _placeholder_image(prompt, frame_path)
        else:
            _placeholder_image(prompt, frame_path)

    return frames_dir


def render_placeholder_frames(job_id: str, prompts: Dict[str, List[str]]) -> Path:
    frames_dir = settings.artifacts_root / job_id / "temp" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    for idx, (scene, parts) in enumerate(prompts.items()):
        prompt = _merge_prompt(parts)
        frame_path = frames_dir / f"{idx:04d}_{scene}.png"
        _placeholder_image(prompt, frame_path)

    return frames_dir
