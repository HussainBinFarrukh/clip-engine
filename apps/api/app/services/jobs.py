import tempfile
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.job import Job, JobStage, JobState
from app.models.media_asset import MediaAsset
from app.models.source_video import SourceVideo, SourceVideoStatus
from app.services.ffprobe import probe_video
from app.services.ingest import store_original_video
from app.services.storage import get_storage_provider
from app.services.youtube import get_youtube_provider

StageHandler = Callable[[Session, Job], dict]


class TestStageFailure(RuntimeError):
    """Raised only by the test_stage handler, to exercise the retry path."""


def enqueue_job(
    db: Session,
    stage: JobStage,
    source_video_id: uuid.UUID | None = None,
    input_json: dict | None = None,
) -> Job:
    job = Job(
        source_video_id=source_video_id,
        stage=stage,
        state=JobState.QUEUED,
        input_json=input_json or {},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _run_test_stage(db: Session, job: Job) -> dict:
    should_fail = job.input_json.get("should_fail", False)
    fail_attempts = job.input_json.get("fail_attempts", 1)
    if should_fail and job.attempts <= fail_attempts:
        raise TestStageFailure(job.input_json.get("failure_message", "test stage failed"))
    return {"ok": True}


def _run_upload_metadata_stage(db: Session, job: Job) -> dict:
    source_video = db.get(SourceVideo, job.source_video_id)
    if source_video is None:
        raise ValueError("source video not found")

    asset = db.get(MediaAsset, uuid.UUID(job.input_json["asset_id"]))
    if asset is None:
        raise ValueError("media asset not found")

    storage = get_storage_provider()
    probe = probe_video(storage.resolve_path(asset.storage_key))

    source_video.duration_ms = probe.duration_ms
    source_video.width = probe.width
    source_video.height = probe.height
    source_video.frame_rate = probe.frame_rate
    source_video.status = SourceVideoStatus.UPLOADED
    source_video.error_message = None

    asset.metadata_json = {
        "duration_ms": probe.duration_ms,
        "width": probe.width,
        "height": probe.height,
        "frame_rate": probe.frame_rate,
    }

    return asset.metadata_json


def _run_youtube_download_stage(db: Session, job: Job) -> dict:
    source_video = db.get(SourceVideo, job.source_video_id)
    if source_video is None:
        raise ValueError("source video not found")

    url = job.input_json["url"]
    provider = get_youtube_provider()
    storage = get_storage_provider()

    with tempfile.TemporaryDirectory() as tmp_dir:
        downloaded = provider.fetch(url, Path(tmp_dir))
        if not source_video.title:
            source_video.title = downloaded.title
        asset = store_original_video(
            db, source_video, storage, downloaded.path, mime_type="video/mp4"
        )

    return {"asset_id": str(asset.id)}


_STAGE_HANDLERS: dict[JobStage, StageHandler] = {
    JobStage.TEST_STAGE: _run_test_stage,
    JobStage.UPLOAD_METADATA: _run_upload_metadata_stage,
    JobStage.YOUTUBE_DOWNLOAD: _run_youtube_download_stage,
}


def execute_job(db: Session, job_id: uuid.UUID) -> Job:
    """Run one attempt of a job's stage.

    Persists the "processing" state (and the incremented attempt count)
    before the stage handler runs, so a crash mid-stage never leaves a
    job silently stuck at "queued". On failure, any partial writes the
    handler made are rolled back so a retry starts from a clean slate;
    only the job's own failure bookkeeping (and the source video's
    failed status, if any) is committed.
    """
    job = db.get(Job, job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")

    job.state = JobState.PROCESSING
    job.attempts += 1
    job.started_at = datetime.now(UTC)
    job.error_code = None
    job.error_message = None
    db.commit()

    handler = _STAGE_HANDLERS[job.stage]
    try:
        output = handler(db, job)
    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        job.state = JobState.FAILED
        job.error_code = type(exc).__name__
        job.error_message = str(exc)[:1000]
        job.completed_at = datetime.now(UTC)
        if job.source_video_id is not None:
            source_video = db.get(SourceVideo, job.source_video_id)
            if source_video is not None:
                source_video.status = SourceVideoStatus.FAILED
                source_video.error_message = job.error_message
        db.commit()
        db.refresh(job)
        return job

    job.output_json = output
    job.progress = 100
    job.state = JobState.COMPLETED
    job.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job
