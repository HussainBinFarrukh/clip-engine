import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobStage(str, enum.Enum):
    TEST_STAGE = "test_stage"
    UPLOAD_METADATA = "upload_metadata"
    YOUTUBE_DOWNLOAD = "youtube_download"
    AUDIO_EXTRACT = "audio_extract"
    TRANSCRIBE = "transcribe"
    SIGNAL_EXTRACTION = "signal_extraction"
    CANDIDATE_SCORING = "candidate_scoring"


class JobState(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_video_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_videos.id", ondelete="CASCADE"), nullable=True
    )
    stage: Mapped[JobStage] = mapped_column(Enum(JobStage, native_enum=False, length=32))
    state: Mapped[JobState] = mapped_column(
        Enum(JobState, native_enum=False, length=32), default=JobState.QUEUED
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
