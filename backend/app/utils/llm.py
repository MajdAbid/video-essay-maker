import logging
import re
from functools import lru_cache
from typing import Dict, List, Optional

try:
    from langchain_openai import ChatOpenAI
except ImportError as exc:  # pragma: no cover - dependency must be installed
    raise RuntimeError(
        "langchain-openai is required for LLM operations. Install it via pip install langchain-openai."
    ) from exc

from .config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache()
def _chat_client() -> ChatOpenAI:
    logger.info(
        "Initialising ChatOpenAI client base_url=%s model=%s",
        settings.llm_base_url,
        settings.llm_model_name,
    )
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "not-needed",
        model=settings.llm_model_name,
        temperature=settings.llm_temperature,
        top_p=settings.llm_top_p,
    )


def generate_script(
    topic: str,
    style: str,
    length_sec: int,
    context: Optional[str] = None,
) -> str:
    template = settings.script_prompt_template or ""
    minutes = max(1, length_sec // 60)
    context_block = ""
    if context:
        clipped = context.strip()
        if len(clipped) > 4000:
            clipped = clipped[:4000].rstrip() + "…"
        context_block = (
            "\n\nUse the following research notes for factual grounding. Do not quote verbatim "
            "unless the facts are accurate and relevant:\n"
            + _escape_braces(clipped)
        )
    prompt = template.format(
        topic=_escape_braces(topic),
        style=_escape_braces(style),
        length_seconds=length_sec,
        minutes=minutes,
        context_block=context_block,
    )

    response = _chat_client().predict(prompt)
    return response.strip()


def generate_transcript(script: str) -> str:
    template = settings.transcript_prompt_template or ""
    clipped = script[:40000]
    prompt = template.format(script=_escape_braces(clipped))
    response = _chat_client().predict(prompt)
    cleaned = response.strip()
    cleaned = re.sub(r"^Transcript:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\S\r\n]+", " ", cleaned)
    return cleaned


def review_script(script: str) -> float:
    template = settings.reviewer_prompt_template or settings.llm_reviewer_prompt
    clipped = script[:6000]
    prompt = template.format(script=_escape_braces(clipped))
    raw = _chat_client().predict(prompt)
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", raw)
    if not match:
        logger.warning("Reviewer response missing numeric score: %s", raw)
        return 0.0
    score = float(match.group(1))
    return round(max(0.0, min(score, 100.0)), 2)


def default_image_prompts(script: str) -> Dict[str, List[str]]:
    paragraphs = [p.strip() for p in script.split("\n") if p.strip()]
    prompts: Dict[str, List[str]] = {}
    for idx, paragraph in enumerate(paragraphs):
        prompts[f"scene_{idx + 1:02d}"] = [
            f"Illustration matching: {paragraph[:120]}",
            "cinematic lighting, 16:9 aspect ratio, ultra-detailed, digital art",
        ]
    return prompts


def _escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")
