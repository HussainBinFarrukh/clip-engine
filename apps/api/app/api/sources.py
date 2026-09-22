import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.media_asset import MediaAsset
from app.models.project import Project
from app.models.source_video import SourceKind, SourceVideo, SourceVideoStatus
from app.schemas.media_asset import MediaAssetRead
from app.schemas.source_video import SourceVideoCreate, SourceVideoRead
from app.services.ingest import store_original_video
from app.services.storage import StorageProvider, get_storage_provider
from app.services.youtube import YouTubeDownloadError, get_youtube_provider

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["sources"])

_ALLOWED_UPLOAD_CONTENT_TYPES = {"video/mp4"}
_ALLOWED_UPLOAD_EXTENSIONS = {".mp4"}


def _get_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_source_or_404(
    db: Session, project_id: uuid.UUID, source_video_id: uuid.UUID
) -> SourceVideo:
    source_video = db.get(SourceVideo, source_video_id)
    if source_video is None or source_video.project_id != project_id:
        raise HTTPException(status_code=404, detail="Source video not found")
    return source_video


def _download_youtube_source(source_video_id: uuid.UUID, url: str) -> None:
    db = SessionLocal()
    storage = get_storage_provider()
    provider = get_youtube_provider()
    try:
        source_video = db.get(SourceVideo, source_video_id)
        if source_video is None:
            return

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                downloaded = provider.fetch(url, Path(tmp_dir))
            except YouTubeDownloadError as exc:
                source_video.status = SourceVideoStatus.FAILED
                source_video.error_message = str(exc)[:1000]
                db.commit()
                return

            if not source_video.title:
                source_video.title = downloaded.title
            store_original_video(db, source_video, storage, downloaded.path, mime_type="video/mp4")
            db.commit()
    finally:
        db.close()


@router.post("", response_model=SourceVideoRead, status_code=201)
def create_source_video(
    project_id: uuid.UUID,
    payload: SourceVideoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SourceVideo:
    _get_project_or_404(db, project_id)

    source_video = SourceVideo(
        project_id=project_id,
        title=payload.title,
        source_kind=payload.source_kind,
        source_reference=payload.source_reference,
        status=SourceVideoStatus.DRAFT,
    )

    if payload.source_kind == SourceKind.YOUTUBE_URL:
        source_video.status = SourceVideoStatus.DOWNLOADING

    db.add(source_video)
    db.commit()
    db.refresh(source_video)

    if payload.source_kind == SourceKind.YOUTUBE_URL:
        background_tasks.add_task(
            _download_youtube_source, source_video.id, payload.source_reference
        )

    return source_video


@router.get("", response_model=list[SourceVideoRead])
def list_source_videos(project_id: uuid.UUID, db: Session = Depends(get_db)) -> list[SourceVideo]:
    _get_project_or_404(db, project_id)
    return list(
        db.scalars(
            select(SourceVideo)
            .where(SourceVideo.project_id == project_id)
            .order_by(SourceVideo.created_at.desc())
        )
    )


@router.get("/{source_video_id}", response_model=SourceVideoRead)
def get_source_video(
    project_id: uuid.UUID, source_video_id: uuid.UUID, db: Session = Depends(get_db)
) -> SourceVideo:
    return _get_source_or_404(db, project_id, source_video_id)


@router.get("/{source_video_id}/assets", response_model=list[MediaAssetRead])
def list_source_assets(
    project_id: uuid.UUID, source_video_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[MediaAsset]:
    _get_source_or_404(db, project_id, source_video_id)
    return list(
        db.scalars(select(MediaAsset).where(MediaAsset.source_video_id == source_video_id))
    )


@router.get("/{source_video_id}/assets/{asset_id}/content")
def stream_source_asset(
    project_id: uuid.UUID,
    source_video_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> StreamingResponse:
    _get_source_or_404(db, project_id, source_video_id)
    asset = db.get(MediaAsset, asset_id)
    if asset is None or asset.source_video_id != source_video_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    if not storage.exists(asset.storage_key):
        raise HTTPException(status_code=404, detail="Asset content not found")

    def _iter_chunks() -> Iterator[bytes]:
        with storage.open_read(asset.storage_key) as stream:
            while chunk := stream.read(1024 * 1024):
                yield chunk

    return StreamingResponse(
        _iter_chunks(),
        media_type=asset.mime_type,
        headers={"Content-Length": str(asset.byte_size)},
    )


@router.post("/{source_video_id}/upload", response_model=SourceVideoRead)
def upload_source_video(
    project_id: uuid.UUID,
    source_video_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> SourceVideo:
    source_video = _get_source_or_404(db, project_id, source_video_id)

    if source_video.source_kind != SourceKind.LOCAL_UPLOAD:
        raise HTTPException(
            status_code=400, detail="Only local_upload sources accept a file upload"
        )

    extension = Path(file.filename or "").suffix.lower()
    valid_content_type = file.content_type in _ALLOWED_UPLOAD_CONTENT_TYPES
    valid_extension = extension in _ALLOWED_UPLOAD_EXTENSIONS
    if not (valid_content_type and valid_extension):
        raise HTTPException(status_code=415, detail="Only MP4 uploads are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_path = Path(tmp_file.name)
        byte_size = 0
        while chunk := file.file.read(1024 * 1024):
            byte_size += len(chunk)
            if byte_size > settings.max_upload_bytes:
                tmp_file.close()
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Upload exceeds the size limit")
            tmp_file.write(chunk)

    try:
        store_original_video(db, source_video, storage, tmp_path, mime_type=file.content_type)
    finally:
        tmp_path.unlink(missing_ok=True)

    db.commit()
    db.refresh(source_video)
    return source_video
