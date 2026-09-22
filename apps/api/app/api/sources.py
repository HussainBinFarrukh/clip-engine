import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.clip_candidate import ClipCandidate
from app.models.job import JobStage
from app.models.media_asset import AssetKind, MediaAsset
from app.models.project import Project
from app.models.signal import Signal
from app.models.source_video import SourceKind, SourceVideo, SourceVideoStatus
from app.models.transcript import Transcript
from app.schemas.clip_candidate import ClipCandidateRead, ScoreCandidatesRequest
from app.schemas.media_asset import MediaAssetRead
from app.schemas.signal import SignalRead
from app.schemas.source_video import SourceVideoCreate, SourceVideoRead
from app.schemas.transcript import TranscriptRead
from app.services.job_queue import dispatch_job
from app.services.jobs import enqueue_job
from app.services.storage import StorageProvider, get_storage_provider

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["sources"])
transcript_router = APIRouter(prefix="/sources", tags=["transcript"])

_TRANSCRIBABLE_STATUSES = {
    SourceVideoStatus.UPLOADED,
    SourceVideoStatus.READY,
    SourceVideoStatus.FAILED,
}

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


@router.post("", response_model=SourceVideoRead, status_code=201)
def create_source_video(
    project_id: uuid.UUID,
    payload: SourceVideoCreate,
    db: Session = Depends(get_db),
) -> SourceVideoRead:
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

    # Snapshot the response before dispatching: dispatch_job hands off to a
    # separate worker process in production, but in tests it may run the
    # job synchronously, which would otherwise expire and silently refresh
    # this object to its post-job state before FastAPI serializes it.
    response = SourceVideoRead.model_validate(source_video)

    if payload.source_kind == SourceKind.YOUTUBE_URL:
        # Enqueued and returned immediately; the download itself runs in the
        # worker process, not within this request (see docs/DECISIONS.md).
        job = enqueue_job(
            db,
            stage=JobStage.YOUTUBE_DOWNLOAD,
            source_video_id=source_video.id,
            input_json={"url": payload.source_reference},
        )
        dispatch_job(job.id)

    return response


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
) -> SourceVideoRead:
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

    asset_id = uuid.uuid4()
    try:
        stored = storage.put_file(str(asset_id), tmp_path, suffix=".mp4")
    finally:
        tmp_path.unlink(missing_ok=True)

    asset = MediaAsset(
        id=asset_id,
        source_video_id=source_video.id,
        asset_kind=AssetKind.ORIGINAL_VIDEO,
        storage_key=stored.storage_key,
        mime_type=file.content_type,
        byte_size=stored.byte_size,
        checksum_sha256=stored.checksum_sha256,
        metadata_json={},
    )
    db.add(asset)
    # The raw bytes are stored synchronously (the request body has to be
    # read here), but probing the file with ffprobe is real media work, so
    # it happens as a job in the worker process, not inline in this request.
    source_video.status = SourceVideoStatus.PROCESSING
    db.commit()
    db.refresh(source_video)

    # See the comment in create_source_video: snapshot before dispatching.
    response = SourceVideoRead.model_validate(source_video)

    job = enqueue_job(
        db,
        stage=JobStage.UPLOAD_METADATA,
        source_video_id=source_video.id,
        input_json={"asset_id": str(asset_id)},
    )
    dispatch_job(job.id)

    return response


@router.post("/{source_video_id}/transcribe", response_model=SourceVideoRead)
def transcribe_source_video(
    project_id: uuid.UUID,
    source_video_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SourceVideoRead:
    source_video = _get_source_or_404(db, project_id, source_video_id)

    if source_video.status not in _TRANSCRIBABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transcribe a source video with status '{source_video.status.value}'",
        )

    source_video.status = SourceVideoStatus.PROCESSING
    source_video.error_message = None
    db.commit()
    db.refresh(source_video)

    # See the comment in create_source_video: snapshot before dispatching.
    response = SourceVideoRead.model_validate(source_video)

    # audio_extract auto-chains into transcribe on success (app.services.jobs).
    job = enqueue_job(db, stage=JobStage.AUDIO_EXTRACT, source_video_id=source_video.id)
    dispatch_job(job.id)

    return response


@router.post("/{source_video_id}/extract-signals", response_model=SourceVideoRead)
def extract_source_signals(
    project_id: uuid.UUID,
    source_video_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SourceVideoRead:
    source_video = _get_source_or_404(db, project_id, source_video_id)

    if source_video.status != SourceVideoStatus.READY:
        raise HTTPException(
            status_code=400,
            detail="Signal extraction needs a transcript first (source must be 'ready')",
        )

    response = SourceVideoRead.model_validate(source_video)

    job = enqueue_job(db, stage=JobStage.SIGNAL_EXTRACTION, source_video_id=source_video.id)
    dispatch_job(job.id)

    return response


@router.get("/{source_video_id}/signals", response_model=list[SignalRead])
def list_source_signals(
    project_id: uuid.UUID, source_video_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[Signal]:
    _get_source_or_404(db, project_id, source_video_id)
    return list(db.scalars(select(Signal).where(Signal.source_video_id == source_video_id)))


@router.post("/{source_video_id}/score-candidates", response_model=SourceVideoRead)
def score_source_candidates(
    project_id: uuid.UUID,
    source_video_id: uuid.UUID,
    payload: ScoreCandidatesRequest | None = None,
    db: Session = Depends(get_db),
) -> SourceVideoRead:
    payload = payload or ScoreCandidatesRequest()
    source_video = _get_source_or_404(db, project_id, source_video_id)

    if source_video.status != SourceVideoStatus.READY:
        raise HTTPException(
            status_code=400,
            detail="Candidate scoring needs a transcript first (source must be 'ready')",
        )
    has_signals = db.scalars(
        select(Signal.id).where(Signal.source_video_id == source_video_id).limit(1)
    ).first()
    if has_signals is None:
        raise HTTPException(
            status_code=400,
            detail="Candidate scoring needs signals extracted first",
        )

    response = SourceVideoRead.model_validate(source_video)

    job = enqueue_job(
        db,
        stage=JobStage.CANDIDATE_SCORING,
        source_video_id=source_video.id,
        input_json={"prompt_version": payload.prompt_version},
    )
    dispatch_job(job.id)

    return response


@router.get("/{source_video_id}/candidates", response_model=list[ClipCandidateRead])
def list_source_candidates(
    project_id: uuid.UUID, source_video_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[ClipCandidate]:
    _get_source_or_404(db, project_id, source_video_id)
    return list(
        db.scalars(
            select(ClipCandidate)
            .where(ClipCandidate.source_video_id == source_video_id)
            .order_by(ClipCandidate.combined_score.desc())
        )
    )


@transcript_router.get("/{source_video_id}/transcript", response_model=TranscriptRead)
def get_source_transcript(source_video_id: uuid.UUID, db: Session = Depends(get_db)) -> Transcript:
    transcript = db.scalars(
        select(Transcript)
        .where(Transcript.source_video_id == source_video_id)
        .order_by(Transcript.created_at.desc())
    ).first()
    if transcript is None:
        raise HTTPException(status_code=404, detail="No transcript for this source video")
    return transcript
