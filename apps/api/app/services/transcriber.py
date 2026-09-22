import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class TranscribedWord:
    word: str
    start_ms: int
    end_ms: int
    confidence: float | None


@dataclass(frozen=True)
class TranscribedSegment:
    start_ms: int
    end_ms: int
    text: str
    confidence: float | None
    words: list[TranscribedWord]


@dataclass(frozen=True)
class TranscriptResult:
    language: str | None
    duration_ms: int
    model_name: str
    segments: list[TranscribedSegment]


class Transcriber(ABC):
    name: str

    @abstractmethod
    def transcribe(self, audio_path: Path) -> TranscriptResult: ...


def _cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


class FasterWhisperTranscriber(Transcriber):
    """faster-whisper adapter: large-v3 on CUDA when available, a smaller
    model on CPU otherwise. Word-level timestamps are always requested."""

    name = "faster-whisper"

    def __init__(self) -> None:
        self._model = None
        self._model_name = ""

    def _load_model(self):
        if self._model is not None:
            return self._model

        from faster_whisper import WhisperModel

        device = os.getenv("WHISPER_DEVICE", "auto")
        if device == "auto":
            device = "cuda" if _cuda_available() else "cpu"

        if device == "cuda":
            model_size = os.getenv("WHISPER_MODEL_CUDA", "large-v3")
            compute_type = "float16"
        else:
            model_size = os.getenv("WHISPER_MODEL_CPU", "tiny")
            compute_type = "int8"

        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self._model_name = model_size
        return self._model

    def transcribe(self, audio_path: Path) -> TranscriptResult:
        model = self._load_model()
        segments_iter, info = model.transcribe(str(audio_path), word_timestamps=True)

        segments: list[TranscribedSegment] = []
        for seg in segments_iter:
            words = [
                TranscribedWord(
                    word=word.word.strip(),
                    start_ms=round(word.start * 1000),
                    end_ms=round(word.end * 1000),
                    confidence=word.probability,
                )
                for word in (seg.words or [])
                if word.word.strip()
            ]
            segments.append(
                TranscribedSegment(
                    start_ms=round(seg.start * 1000),
                    end_ms=round(seg.end * 1000),
                    text=seg.text.strip(),
                    confidence=seg.avg_logprob,
                    words=words,
                )
            )

        return TranscriptResult(
            language=info.language,
            duration_ms=round(info.duration * 1000),
            model_name=self._model_name,
            segments=segments,
        )


@lru_cache
def get_transcriber() -> Transcriber:
    return FasterWhisperTranscriber()
