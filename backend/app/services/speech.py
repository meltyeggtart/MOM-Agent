"""Speech to text.

Production targets Amazon Transcribe, but no AWS credentials exist yet, so a local
Whisper model runs in its place. Both satisfy the same one-method seam, so swapping the
provider touches this file only. See PROGRESS.md.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.settings import settings


@dataclass(frozen=True)
class Segment:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class SpeechResult:
    text: str
    language: str
    provider: str
    segments: list[Segment]


class SpeechToText(Protocol):
    provider: str

    def transcribe(self, audio_path: Path, language: str) -> SpeechResult: ...


class WhisperSpeechToText:
    provider = "faster-whisper"

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.whisper_model
        self._model = None

    def _model_instance(self):
        if self._model is None:
            # Imported lazily so the API starts without loading a model.
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self._model_name, device="cpu", compute_type="int8"
            )
        return self._model

    def transcribe(self, audio_path: Path, language: str) -> SpeechResult:
        segments, info = self._model_instance().transcribe(
            str(audio_path), language=language, beam_size=1
        )
        items = [
            Segment(
                start_ms=round(segment.start * 1000),
                end_ms=round(segment.end * 1000),
                text=segment.text.strip(),
            )
            for segment in segments
        ]
        return SpeechResult(
            text=" ".join(item.text for item in items).strip(),
            language=info.language,
            provider=self.provider,
            segments=items,
        )


@lru_cache
def get_speech_to_text() -> SpeechToText:
    return WhisperSpeechToText()
