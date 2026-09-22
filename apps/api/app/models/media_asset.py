import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.source_video import SourceVideo


class AssetKind(str, enum.Enum):
    ORIGINAL_VIDEO = "original_video"
    EXTRACTED_AUDIO = "extracted_audio"
    THUMBNAIL = "thumbnail"
    ANALYSIS_ARTIFACT = "analysis_artifact"


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_videos.id", ondelete="CASCADE")
    )
    asset_kind: Mapped[AssetKind] = mapped_column(Enum(AssetKind, native_enum=False, length=32))
    storage_key: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(200))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_video: Mapped["SourceVideo"] = relationship(back_populates="media_assets")
