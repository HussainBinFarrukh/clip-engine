import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TranscriptWordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    word: str
    start_ms: int
    end_ms: int
    confidence: float | None
    word_index: int


class TranscriptSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    start_ms: int
    end_ms: int
    text: str
    speaker_label: str | None
    confidence: float | None
    words: list[TranscriptWordRead]


class TranscriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_video_id: uuid.UUID
    transcriber_name: str
    transcriber_model: str
    language: str | None
    duration_ms: int
    created_at: datetime
    segments: list[TranscriptSegmentRead]
