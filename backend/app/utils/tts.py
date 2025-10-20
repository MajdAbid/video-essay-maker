import logging
import wave
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

from .config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()
logging.getLogger("phonemizer").setLevel(logging.ERROR)
logging.getLogger("phonemizer.backend.espeak.words_mismatch").setLevel(logging.ERROR)


@lru_cache()
def _kokoro_service():  # pragma: no cover - heavy dependency
    from ..integrations.audio.kokoro import KokoroTTSService

    return KokoroTTSService(device="cpu")


def _synthesize_with_kokoro(script: str, voice: Optional[str], audio_path: Path) -> Path:
    service = _kokoro_service()
    chosen_voice = voice or settings.tts_voice or "Nova"
    try:
        sample_rate, audio_chunk = service.synthesize_speech(
            script,
            voice=chosen_voice,
            speed=settings.tts_speed,
        )
    except ValueError:
        # Unknown voice label, fallback to default
        sample_rate, audio_chunk = service.synthesize_speech(
            script,
            voice="Nova",
            speed=settings.tts_speed,
        )

    with wave.open(str(audio_path), "wb") as wav_fh:
        wav_fh.setnchannels(1)
        wav_fh.setsampwidth(2)
        wav_fh.setframerate(sample_rate)
        pcm = np.clip(audio_chunk * 32767, -32768, 32767).astype("<i2")
        wav_fh.writeframes(pcm.tobytes())
    return audio_path


def _synthesize_with_coqui(script: str, voice: Optional[str], audio_path: Path) -> Path:
    try:
        from TTS.api import TTS

        model = settings.tts_model_name
        logger.info("Synthesizing audio using model %s", model)
        tts = TTS(model_name=model)
        tts.tts_to_file(text=script, speaker=voice, file_path=str(audio_path))
        return audio_path
    except Exception as exc:  # noqa: BLE001
        logger.warning("Coqui TTS failed (%s). Falling back to gTTS.", exc)
        from gtts import gTTS

        tts = gTTS(text=script, lang="en")
        tts.save(str(audio_path))
        return audio_path


def synthesize(job_id: str, script: str, voice: Optional[str] = None) -> Path:
    """Generate narration audio for a script using the configured provider."""

    output_dir = settings.artifacts_root / job_id / "temp"
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "audio.wav"

    provider = (settings.tts_provider or "coqui").lower()
    if provider == "kokoro":
        try:
            return _synthesize_with_kokoro(script, voice, audio_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kokoro synthesis failed (%s). Falling back to Coqui.", exc)

    return _synthesize_with_coqui(script, voice, audio_path)
