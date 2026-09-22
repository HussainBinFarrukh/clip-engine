import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.media_asset import AssetKind, MediaAsset
from app.models.source_video import SourceVideo, SourceVideoStatus
from app.services.ffprobe import FFProbeError, probe_video
from app.services.storage import StorageProvider


def store_original_video(
    db: Session,
    source_video: SourceVideo,
    storage: StorageProvider,
    file_path: Path,
    mime_type: str,
) -> MediaAsset:
    """Move a downloaded/uploaded video into storage, probe it, and record it.

    Updates source_video's metadata and status in place. Caller commits.
    """
    asset_id = str(uuid.uuid4())
    stored = storage.put_file(asset_id, file_path, suffix=".mp4")

    try:
        probe = probe_video(storage.resolve_path(stored.storage_key))
        probe_metadata = {
            "duration_ms": probe.duration_ms,
            "width": probe.width,
            "height": probe.height,
            "frame_rate": probe.frame_rate,
        }
        source_video.duration_ms = probe.duration_ms
        source_video.width = probe.width
        source_video.height = probe.height
        source_video.frame_rate = probe.frame_rate
    except FFProbeError as exc:
        probe_metadata = {"error": str(exc)}

    asset = MediaAsset(
        id=uuid.UUID(asset_id),
        source_video_id=source_video.id,
        asset_kind=AssetKind.ORIGINAL_VIDEO,
        storage_key=stored.storage_key,
        mime_type=mime_type,
        byte_size=stored.byte_size,
        checksum_sha256=stored.checksum_sha256,
        metadata_json=probe_metadata,
    )
    db.add(asset)

    source_video.status = SourceVideoStatus.UPLOADED
    source_video.error_message = None

    return asset
