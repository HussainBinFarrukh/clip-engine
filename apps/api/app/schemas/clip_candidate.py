import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    feature_vector: dict
    model: str
    prompt_name: str
    prompt_version: int
    created_at: datetime
