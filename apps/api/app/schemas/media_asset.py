import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.media_asset import AssetKind


class MediaAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_video_id: uuid.UUID
    asset_kind: AssetKind
    mime_type: str
    byte_size: int
    checksum_sha256: str
    metadata_json: dict
    created_at: datetime
