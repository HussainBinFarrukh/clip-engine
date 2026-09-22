import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.signal import SignalType


class SignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_video_id: uuid.UUID
    signal_type: SignalType
    unit: str
    points_json: list[dict]
    created_at: datetime
