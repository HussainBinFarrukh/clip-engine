import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.media_asset import MediaAsset
    from app.models.project import Project


class SourceKind(str, enum.Enum):
    LOCAL_UPLOAD = "local_upload"
    YOUTUBE_URL = "youtube_url"


class SourceVideoStatus(str, enum.Enum):
    DRAFT = "draft"
    UPLOADED = "uploaded"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class SourceVideo(Base):
    __tablename__ = "source_videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(300))
    source_kind: Mapped[SourceKind] = mapped_column(Enum(SourceKind, native_enum=False, length=32))
    source_reference: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_rate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[SourceVideoStatus] = mapped_column(
        Enum(SourceVideoStatus, native_enum=False, length=32),
        default=SourceVideoStatus.DRAFT,
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="source_videos")
    media_assets: Mapped[list["MediaAsset"]] = relationship(
        back_populates="source_video", cascade="all, delete-orphan"
    )
