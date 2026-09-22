import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClipCandidate(Base):
    """A scored candidate window. Re-scoring the same (source_video, preset,
    prompt_name, prompt_version) replaces those rows (idempotent retry);
    scoring under a *new* prompt_version adds alongside old rows rather
    than replacing them, so old results survive a prompt change — see
    docs/DECISIONS.md."""

    __tablename__ = "clip_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_videos.id", ondelete="CASCADE")
    )
    preset: Mapped[str] = mapped_column(String(50))
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)

    heuristic_score: Mapped[float] = mapped_column(Float)
    llm_score: Mapped[float] = mapped_column(Float)
    combined_score: Mapped[float] = mapped_column(Float)

    hook_line: Mapped[bool] = mapped_column(Boolean)
    self_contained: Mapped[bool] = mapped_column(Boolean)
    emotional_peak: Mapped[bool] = mapped_column(Boolean)
    quotable_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text)

    feature_vector: Mapped[dict] = mapped_column(JSON)

    model: Mapped[str] = mapped_column(String(100))
    prompt_name: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms
