import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.job import JobStage, JobState


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_video_id: uuid.UUID | None
    stage: JobStage
    state: JobState
    progress: int
    attempts: int
    error_code: str | None
    error_message: str | None
    output_json: dict
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
