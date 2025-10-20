from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Optional

import typer

from .utils import imggen, llm, tts, video


cli = typer.Typer(help="Command-line utilities for the video generation pipeline.")


@cli.command("generate-script")
def generate_script(
    topic: str = typer.Argument(...),
    style: str = typer.Argument(...),
    length: int = typer.Argument(..., help="Desired length in seconds"),
    output: Path = typer.Option(Path("script.txt"), "--output", "-o"),
    transcript_output: Path = typer.Option(
        Path("transcript.txt"),
        "--transcript-output",
        "-t",
        help="Where to store the generated narration transcript.",
    ),
    context: Optional[str] = typer.Option(None, "--context", help="Inline context text"),
    context_file: Optional[Path] = typer.Option(
        None, "--context-file", help="Path to a file containing context text"
    ),
) -> None:
    context_text = context
    if context_file and context_file.exists():
        context_text = context_file.read_text(encoding="utf-8")

    script = llm.generate_script(topic, style, length, context=context_text)
    transcript = llm.generate_transcript(script)
    output.write_text(script, encoding="utf-8")
    transcript_output.write_text(transcript, encoding="utf-8")
    typer.echo(f"Wrote script to {output}")
    typer.echo(f"Wrote transcript to {transcript_output}")


@cli.command("review-script")
def review_script(
    script_path: Path = typer.Argument(Path("script.txt")),
    output: Path = typer.Option(Path("review_score.txt"), "--output", "-o"),
) -> None:
    script = script_path.read_text(encoding="utf-8")
    score = llm.review_script(script)
    output.write_text(str(score), encoding="utf-8")
    typer.echo(f"Review score: {score}")


@cli.command("tts")
def synthesize_audio(
    job_id: str = typer.Argument(...),
    text_path: Path = typer.Argument(Path("transcript.txt")),
    output: Path = typer.Option(Path("audio.wav"), "--output", "-o"),
) -> None:
    narration_text = text_path.read_text(encoding="utf-8")
    audio_path = tts.synthesize(job_id, narration_text)
    Path(audio_path).replace(output)
    typer.echo(f"Generated audio at {output}")


@cli.command("render-frames")
def render_frames(
    job_id: str = typer.Argument(...),
    prompts_json: Path = typer.Argument(Path("prompts.json")),
    output: Path = typer.Option(Path("image.png"), "--output", "-o"),
) -> None:
    prompts = json.loads(prompts_json.read_text(encoding="utf-8"))
    if isinstance(prompts, dict) and prompts:
        prompt_parts = next(iter(prompts.values()))
    elif isinstance(prompts, list):
        prompt_parts = prompts
    else:
        prompt_parts = [""]
    image_path = imggen.render_cover_image(job_id, prompt_parts)
    output.parent.mkdir(parents=True, exist_ok=True)
    if image_path != output:
        shutil.copy2(image_path, output)
    typer.echo(f"Cover image stored at {output}")


@cli.command("prompts")
def export_prompts(
    script_path: Path = typer.Argument(Path("script.txt")),
    output: Path = typer.Option(Path("prompts.json"), "--output", "-o"),
) -> None:
    script = script_path.read_text(encoding="utf-8")
    prompts = llm.default_image_prompts(script)
    output.write_text(json.dumps(prompts, indent=2), encoding="utf-8")
    typer.echo(f"Prompts saved to {output}")


@cli.command("assemble")
def assemble_video(
    job_id: str = typer.Argument(...),
    image_path: Path = typer.Argument(Path("image.png")),
    audio_path: Path = typer.Argument(Path("audio.wav")),
    output: Path = typer.Option(Path("final.mp4"), "--output", "-o"),
) -> None:
    produced = video.assemble_static(job_id, image_path, audio_path)
    Path(produced).replace(output)
    typer.echo(f"Video assembled at {output}")


if __name__ == "__main__":
    cli()
