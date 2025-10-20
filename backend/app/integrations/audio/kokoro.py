"""Kokoro TTS integration adapted from the VideoMaker project."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, Iterator, Optional, Sequence, Tuple

import numpy as np
import torch

from kokoro import KModel, KPipeline

SAMPLE_RATE = 24_000

DEFAULT_VOICE_CHOICES: Dict[str, str] = {
    "Alloy": "af_alloy",
    "Aoede": "af_aoede",
    "Bella": "af_bella",
    "Heart": "af_heart",
    "Jessica": "af_jessica",
    "Kore": "af_kore",
    "Nicole": "af_nicole",
    "Nova": "af_nova",
    "River": "af_river",
    "Sarah": "af_sarah",
    "Sky": "af_sky",
    "Adam": "am_adam",
    "Echo": "am_echo",
    "Eric": "am_eric",
    "Fenrir": "am_fenrir",
    "Liam": "am_liam",
    "Michael": "am_michael",
    "Onyx": "am_onyx",
    "Puck": "am_puck",
    "Alice": "bf_alice",
    "Emma": "bf_emma",
    "Isabella": "bf_isabella",
    "Lily": "bf_lily",
    "Daniel": "bm_daniel",
    "Fable": "bm_fable",
    "George": "bm_george",
    "Lewis": "bm_lewis",
    "Siwis": "ff_siwis",
    "Sara": "if_sara",
    "Nicola": "im_nicola",
    "Alpha": "jf_alpha",
    "Gongitsune": "jf_gongitsune",
    "Nezumi": "jf_nezumi",
    "Tebukuro": "jf_tebukuro",
    "Kumo": "jm_kumo",
    "Xiaobei": "zf_xiaobei",
    "Xiaoni": "zf_xiaoni",
    "Xiaoxiao": "zf_xiaoxiao",
    "Xiaoyi": "zf_xiaoyi",
    "Yunjian": "zm_yunjian",
    "Yunxi": "zm_yunxi",
    "Yunxia": "zm_yunxia",
    "Yunyang": "zm_yunyang",
}


@dataclass(frozen=True)
class VoiceInfo:
    label: str
    voice_id: str


class KokoroTTSService:
    """Utility wrapper around Kokoro pipelines."""

    def __init__(self, *, device: Optional[str] = None, voice_map: Optional[Dict[str, str]] = None):
        self.device = device or self._auto_device()
        self.voice_map: Dict[str, str] = dict(voice_map or DEFAULT_VOICE_CHOICES)
        self._model: Optional[KModel] = None
        self._pipelines: Dict[str, KPipeline] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _auto_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():  # type: ignore[attr-defined]
            return "mps"
        return "cpu"

    def _ensure_model(self) -> KModel:
        if self._model is None:
            self._model = KModel().to(self.device).eval()
        return self._model

    def _ensure_pipeline(self, voice_id: str) -> Tuple[KPipeline, Sequence]:
        lang_code = voice_id[0]
        pipeline = self._pipelines.get(lang_code)
        if pipeline is None:
            pipeline = KPipeline(lang_code=lang_code, model=False)
            self._pipelines[lang_code] = pipeline
        pack = pipeline.load_voice(voice_id)
        return pipeline, pack

    def list_voices(self) -> Tuple[VoiceInfo, ...]:
        return tuple(VoiceInfo(label, voice_id) for label, voice_id in self.voice_map.items())

    def resolve_voice(self, voice: Optional[str]) -> VoiceInfo:
        if voice is None:
            raise ValueError("Voice must be provided (label or voice id).")
        if voice in self.voice_map:
            return VoiceInfo(label=voice, voice_id=self.voice_map[voice])
        if any(voice == vid for vid in self.voice_map.values()):
            return VoiceInfo(label=voice, voice_id=voice)
        raise ValueError(f"Unknown voice '{voice}'.")

    def stream_speech(
        self,
        text: str,
        *,
        voice: str,
        speed: float = 1.0,
        insert_leading_silence: bool = True,
    ) -> Iterator[Tuple[int, np.ndarray]]:
        text = text.strip()
        if not text:
            return iter(())

        voice_info = self.resolve_voice(voice)

        def _generate() -> Iterator[Tuple[int, np.ndarray]]:
            with self._lock:
                model = self._ensure_model()
                pipeline, pack = self._ensure_pipeline(voice_info.voice_id)
                first_chunk_emitted = False
                silence_sent = False
                with torch.inference_mode():
                    for _, phoneme_seq, _ in pipeline(text, voice_info.voice_id, speed):
                        ref_slice = pack[len(phoneme_seq) - 1]
                        audio = model(phoneme_seq, ref_slice, speed)
                        chunk = audio.detach().cpu().numpy()
                        yield SAMPLE_RATE, chunk
                        first_chunk_emitted = True
                        if insert_leading_silence and not silence_sent:
                            silence_sent = True
                            yield SAMPLE_RATE, np.zeros(1, dtype=np.float32)
                    if insert_leading_silence and not first_chunk_emitted and not silence_sent:
                        yield SAMPLE_RATE, np.zeros(1, dtype=np.float32)

        return _generate()

    def synthesize_speech(self, text: str, *, voice: str, speed: float = 1.0) -> Tuple[int, np.ndarray]:
        chunks = []
        sample_rate = SAMPLE_RATE
        for sample_rate, chunk in self.stream_speech(
            text,
            voice=voice,
            speed=speed,
            insert_leading_silence=False,
        ):
            chunks.append(chunk)

        if not chunks:
            return sample_rate, np.zeros(0, dtype=np.float32)

        audio = np.concatenate(chunks)
        return sample_rate, audio


__all__ = ["KokoroTTSService", "VoiceInfo", "DEFAULT_VOICE_CHOICES", "SAMPLE_RATE"]
