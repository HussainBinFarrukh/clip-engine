import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SignalType(str, enum.Enum):
    LOUDNESS_RMS = "loudness_rms"
    SCENE_CHANGE = "scene_change"
    PAUSE = "pause"
    SPEECH_RATE = "speech_rate"


class Signal(Base):
    """One time series per (source_video, signal_type).

    `points_json` is a list of dicts, always `t_ms`-keyed, with a shape
    that depends on `signal_type`:
      - loudness_rms:  {t_ms, value}       value = dBFS
      - speech_rate:   {t_ms, value}       value = words per minute
      - scene_change:  {t_ms}              a detected cut
      - pause:         {t_ms, duration_ms} a gap between words
    """

    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_videos.id", ondelete="CASCADE")
    )
    signal_type: Mapped[SignalType] = mapped_column(
        Enum(SignalType, native_enum=False, length=32)
    )
    unit: Mapped[str] = mapped_column(String(32))
    points_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
