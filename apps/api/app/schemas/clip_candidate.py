import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.clip_candidate import ReviewStatus


class ScoreCandidatesRequest(BaseModel):
    prompt_version: int = Field(default=1, ge=1)


class ClipCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_video_id: uuid.UUID
    preset: str
    start_ms: int
    end_ms: int
    heuristic_score: float
    llm_score: float
    combined_score: float
    hook_line: bool
    self_contained: bool
    emotional_peak: bool
    quotable_line: str | None
    reason: str
    transcript_excerpt: str
    feature_vector: dict
    model: str
    prompt_name: str
    prompt_version: int
    review_status: ReviewStatus
    created_at: datetime


class ClipCandidateUpdate(BaseModel):
    """PATCH body: adjust times, set review status, or both in one call."""

    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    review_status: ReviewStatus | None = None

    @model_validator(mode="after")
    def _both_times_or_neither(self) -> "ClipCandidateUpdate":
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError("start_ms and end_ms must be provided together")
        if self.start_ms is not None and self.end_ms is not None and self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be before end_ms")
        return self
