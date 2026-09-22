import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.source_video import SourceKind, SourceVideoStatus

_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


class SourceVideoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    source_kind: SourceKind
    source_reference: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def _validate_reference(self) -> "SourceVideoCreate":
        if self.source_kind == SourceKind.YOUTUBE_URL:
            if not self.source_reference:
                raise ValueError("source_reference is required for source_kind youtube_url")
            from urllib.parse import urlparse

            host = urlparse(self.source_reference).hostname or ""
            if host not in _YOUTUBE_HOSTS:
                raise ValueError("source_reference must be a youtube.com or youtu.be URL")
        elif self.source_reference is not None:
            raise ValueError("source_reference is only used for source_kind youtube_url")
        return self


class SourceVideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    source_kind: SourceKind
    source_reference: str | None
    duration_ms: int | None
    width: int | None
    height: int | None
    frame_rate: str | None
    status: SourceVideoStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
