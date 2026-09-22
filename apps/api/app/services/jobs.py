import tempfile
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clip_candidate import ClipCandidate
from app.models.job import Job, JobStage, JobState
from app.models.media_asset import AssetKind, MediaAsset
from app.models.signal import Signal, SignalType
from app.models.source_video import SourceVideo, SourceVideoStatus
from app.models.transcript import Transcript, TranscriptSegment, TranscriptWord
from app.services.ai_analysis import run_llm_call
from app.services.candidate_scoring import (
    ClipCandidateScore,
    compute_heuristic_features,
    deduplicate_windows,
    heuristic_score,
)
from app.services.candidate_windows import (
    CandidateWindow,
    SentenceBoundary,
    generate_candidate_windows,
)
from app.services.clip_presets import CLIP_PRESETS
from app.services.ffmpeg import extract_audio_16k_mono_wav
from app.services.ffprobe import probe_video
from app.services.ingest import store_original_video
from app.services.job_queue import dispatch_job as _default_dispatch_job
from app.services.llm_provider import LLMStructuredOutputError, get_llm_provider
from app.services.prompts import load_prompt
from app.services.signals import (
    compute_loudness_rms,
    compute_pauses,
    compute_scene_changes,
    compute_speech_rate,
)
from app.services.storage import get_storage_provider
from app.services.transcriber import TranscriptResult, get_transcriber
from app.services.youtube import get_youtube_provider

_MAX_CANDIDATES_PER_PRESET = 3
_DEDUP_IOU_THRESHOLD = 0.5
# (heuristic weight, LLM weight) — the LLM's qualitative read dominates;
# heuristics are a cheap sanity signal. Tunable, not tuned — see
# app.services.candidate_scoring.heuristic_score's own docstring.
_COMBINED_SCORE_WEIGHTS = (0.3, 0.7)

StageHandler = Callable[[Session, Job], dict]
Dispatcher = Callable[[uuid.UUID], None]

# A stage that, on success, automatically enqueues the next one. Kept
# deliberately narrow: upload_metadata/youtube_download do NOT auto-chain
# into audio_extract — transcription is compute-heavy, so the user
# explicitly starts it (POST .../transcribe) rather than it firing on
# every upload. audio_extract -> transcribe are a tightly coupled pair,
# so once transcription is requested the whole pair runs without a
# second click.
_NEXT_STAGE: dict[JobStage, JobStage] = {
    JobStage.AUDIO_EXTRACT: JobStage.TRANSCRIBE,
}


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


def _latest_asset(db: Session, source_video_id: uuid.UUID, asset_kind: AssetKind) -> MediaAsset:
    asset = db.scalars(
        select(MediaAsset)
        .where(
            MediaAsset.source_video_id == source_video_id,
            MediaAsset.asset_kind == asset_kind,
        )
        .order_by(MediaAsset.created_at.desc())
        .limit(1)
    ).first()
    if asset is None:
        raise ValueError(f"no {asset_kind.value} asset found for source video {source_video_id}")
    return asset


def _run_audio_extract_stage(db: Session, job: Job) -> dict:
    source_video = db.get(SourceVideo, job.source_video_id)
    if source_video is None:
        raise ValueError("source video not found")

    storage = get_storage_provider()
    original = _latest_asset(db, source_video.id, AssetKind.ORIGINAL_VIDEO)

    with tempfile.TemporaryDirectory() as tmp_dir:
        wav_path = Path(tmp_dir) / "audio.wav"
        extract_audio_16k_mono_wav(storage.resolve_path(original.storage_key), wav_path)

        asset_id = uuid.uuid4()
        stored = storage.put_file(str(asset_id), wav_path, suffix=".wav")

    asset = MediaAsset(
        id=asset_id,
        source_video_id=source_video.id,
        asset_kind=AssetKind.EXTRACTED_AUDIO,
        storage_key=stored.storage_key,
        mime_type="audio/wav",
        byte_size=stored.byte_size,
        checksum_sha256=stored.checksum_sha256,
        metadata_json={"sample_rate_hz": 16000, "channels": 1},
    )
    db.add(asset)

    return {"asset_id": str(asset_id)}


def _save_transcript(
    db: Session, source_video_id: uuid.UUID, transcriber_name: str, result: TranscriptResult
) -> Transcript:
    # Delete-then-insert keeps re-running this stage idempotent: no
    # duplicate transcripts accumulate across retries or re-transcription.
    existing = db.scalars(
        select(Transcript).where(Transcript.source_video_id == source_video_id)
    ).all()
    for old in existing:
        db.delete(old)
    db.flush()

    transcript = Transcript(
        source_video_id=source_video_id,
        transcriber_name=transcriber_name,
        transcriber_model=result.model_name,
        language=result.language,
        duration_ms=result.duration_ms,
    )
    db.add(transcript)
    db.flush()

    for segment in result.segments:
        segment_row = TranscriptSegment(
            transcript_id=transcript.id,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            text=segment.text,
            confidence=segment.confidence,
        )
        db.add(segment_row)
        db.flush()

        for index, word in enumerate(segment.words):
            db.add(
                TranscriptWord(
                    segment_id=segment_row.id,
                    start_ms=word.start_ms,
                    end_ms=word.end_ms,
                    word=word.word,
                    confidence=word.confidence,
                    word_index=index,
                )
            )

    return transcript


def _run_transcribe_stage(db: Session, job: Job) -> dict:
    source_video = db.get(SourceVideo, job.source_video_id)
    if source_video is None:
        raise ValueError("source video not found")

    storage = get_storage_provider()
    audio_asset = _latest_asset(db, source_video.id, AssetKind.EXTRACTED_AUDIO)

    transcriber = get_transcriber()
    result = transcriber.transcribe(storage.resolve_path(audio_asset.storage_key))

    transcript = _save_transcript(db, source_video.id, transcriber.name, result)
    source_video.status = SourceVideoStatus.READY
    source_video.error_message = None

    word_count = sum(len(segment.words) for segment in result.segments)
    return {
        "transcript_id": str(transcript.id),
        "language": result.language,
        "segment_count": len(result.segments),
        "word_count": word_count,
    }


def _save_signal(
    db: Session, source_video_id: uuid.UUID, signal_type: SignalType, unit: str, points: list[dict]
) -> Signal:
    # Delete-then-insert, same idempotency pattern as _save_transcript: no
    # duplicate series pile up across retries or re-runs.
    existing = db.scalars(
        select(Signal).where(
            Signal.source_video_id == source_video_id, Signal.signal_type == signal_type
        )
    ).all()
    for old in existing:
        db.delete(old)
    db.flush()

    signal = Signal(
        source_video_id=source_video_id, signal_type=signal_type, unit=unit, points_json=points
    )
    db.add(signal)
    return signal


def _run_signal_extraction_stage(db: Session, job: Job) -> dict:
    source_video = db.get(SourceVideo, job.source_video_id)
    if source_video is None:
        raise ValueError("source video not found")

    transcript = db.scalars(
        select(Transcript)
        .where(Transcript.source_video_id == source_video.id)
        .order_by(Transcript.created_at.desc())
    ).first()
    if transcript is None:
        raise ValueError("source video has no transcript yet")

    segments = [
        {
            "start_ms": segment.start_ms,
            "end_ms": segment.end_ms,
            "words": [{"start_ms": w.start_ms, "end_ms": w.end_ms} for w in segment.words],
        }
        for segment in transcript.segments
    ]
    words = [word for segment in segments for word in segment["words"]]

    storage = get_storage_provider()
    original = _latest_asset(db, source_video.id, AssetKind.ORIGINAL_VIDEO)
    audio = _latest_asset(db, source_video.id, AssetKind.EXTRACTED_AUDIO)

    loudness = compute_loudness_rms(storage.resolve_path(audio.storage_key))
    scene_changes = compute_scene_changes(storage.resolve_path(original.storage_key))
    pauses = compute_pauses(words)
    speech_rate = compute_speech_rate(segments)

    _save_signal(db, source_video.id, SignalType.LOUDNESS_RMS, "dbfs", loudness)
    _save_signal(db, source_video.id, SignalType.SCENE_CHANGE, "event", scene_changes)
    _save_signal(db, source_video.id, SignalType.PAUSE, "ms", pauses)
    _save_signal(db, source_video.id, SignalType.SPEECH_RATE, "wpm", speech_rate)

    return {
        "loudness_points": len(loudness),
        "scene_changes": len(scene_changes),
        "pauses": len(pauses),
        "speech_rate_points": len(speech_rate),
    }


def _save_clip_candidates_for_version(
    db: Session,
    source_video_id: uuid.UUID,
    preset_name: str,
    prompt_name: str,
    prompt_version: int,
    candidates: list[ClipCandidate],
) -> None:
    # Replaces prior candidates for this exact (preset, prompt_version) —
    # idempotent retry — but leaves other prompt_versions' rows alone, so
    # re-scoring under a new prompt version doesn't erase old results. See
    # docs/DECISIONS.md.
    existing = db.scalars(
        select(ClipCandidate).where(
            ClipCandidate.source_video_id == source_video_id,
            ClipCandidate.preset == preset_name,
            ClipCandidate.prompt_name == prompt_name,
            ClipCandidate.prompt_version == prompt_version,
        )
    ).all()
    for old in existing:
        db.delete(old)
    db.flush()
    for candidate in candidates:
        db.add(candidate)


def _run_candidate_scoring_stage(db: Session, job: Job) -> dict:
    source_video = db.get(SourceVideo, job.source_video_id)
    if source_video is None:
        raise ValueError("source video not found")

    transcript = db.scalars(
        select(Transcript)
        .where(Transcript.source_video_id == source_video.id)
        .order_by(Transcript.created_at.desc())
    ).first()
    if transcript is None:
        raise ValueError("source video has no transcript yet")

    signal_rows = db.scalars(
        select(Signal).where(Signal.source_video_id == source_video.id)
    ).all()
    if not signal_rows:
        raise ValueError("source video has no signals extracted yet")
    signals_by_type = {s.signal_type: s.points_json for s in signal_rows}
    loudness = signals_by_type.get(SignalType.LOUDNESS_RMS, [])
    pauses = signals_by_type.get(SignalType.PAUSE, [])
    speech_rate = signals_by_type.get(SignalType.SPEECH_RATE, [])
    scene_changes = signals_by_type.get(SignalType.SCENE_CHANGE, [])

    ordered_segments = sorted(transcript.segments, key=lambda s: s.start_ms)
    sentences = [
        SentenceBoundary(index=i, start_ms=s.start_ms, end_ms=s.end_ms)
        for i, s in enumerate(ordered_segments)
    ]

    prompt_version = job.input_json.get("prompt_version", 1)
    prompt_template = load_prompt("clip_scoring", prompt_version)
    provider = get_llm_provider()

    total_scored = 0
    total_failed = 0
    presets_with_candidates: list[str] = []

    for preset in CLIP_PRESETS.values():
        windows = generate_candidate_windows(sentences, preset)
        if not windows:
            continue

        features_by_window: dict[CandidateWindow, tuple] = {}
        scored_for_dedup: list[tuple[CandidateWindow, float]] = []
        for window in windows:
            features = compute_heuristic_features(
                window, loudness, pauses, speech_rate, scene_changes
            )
            h_score = heuristic_score(features)
            features_by_window[window] = (features, h_score)
            scored_for_dedup.append((window, h_score))

        deduped = deduplicate_windows(
            scored_for_dedup,
            iou_threshold=_DEDUP_IOU_THRESHOLD,
            max_keep=_MAX_CANDIDATES_PER_PRESET,
        )

        new_candidates: list[ClipCandidate] = []
        for window in deduped:
            features, h_score = features_by_window[window]
            transcript_text = " ".join(
                ordered_segments[i].text
                for i in range(window.start_sentence_index, window.end_sentence_index + 1)
            )
            prompt = prompt_template.format(
                preset=preset.name,
                duration_s=window.duration_ms / 1000,
                transcript_text=transcript_text,
            )

            try:
                score = run_llm_call(
                    db,
                    provider,
                    "clip_scoring",
                    prompt_version,
                    prompt,
                    ClipCandidateScore,
                    source_video_id=source_video.id,
                )
            except LLMStructuredOutputError:
                total_failed += 1
                continue

            heuristic_weight, llm_weight = _COMBINED_SCORE_WEIGHTS
            combined = round(heuristic_weight * h_score + llm_weight * score.score, 1)

            new_candidates.append(
                ClipCandidate(
                    source_video_id=source_video.id,
                    preset=preset.name,
                    start_ms=window.start_ms,
                    end_ms=window.end_ms,
                    heuristic_score=h_score,
                    llm_score=float(score.score),
                    combined_score=combined,
                    hook_line=score.hook_line,
                    self_contained=score.self_contained,
                    emotional_peak=score.emotional_peak,
                    quotable_line=score.quotable_line,
                    reason=score.reason,
                    feature_vector={
                        "avg_loudness_dbfs": features.avg_loudness_dbfs,
                        "pause_ratio": features.pause_ratio,
                        "avg_speech_rate_wpm": features.avg_speech_rate_wpm,
                        "scene_change_count": features.scene_change_count,
                    },
                    model=provider.model,
                    prompt_name="clip_scoring",
                    prompt_version=prompt_version,
                )
            )
            total_scored += 1

        if new_candidates:
            _save_clip_candidates_for_version(
                db, source_video.id, preset.name, "clip_scoring", prompt_version, new_candidates
            )
            presets_with_candidates.append(preset.name)

    if total_scored == 0 and total_failed > 0:
        raise RuntimeError(f"all {total_failed} candidate scoring call(s) failed")

    return {
        "candidates_scored": total_scored,
        "candidates_failed": total_failed,
        "presets": presets_with_candidates,
        "prompt_version": prompt_version,
    }


_STAGE_HANDLERS: dict[JobStage, StageHandler] = {
    JobStage.TEST_STAGE: _run_test_stage,
    JobStage.UPLOAD_METADATA: _run_upload_metadata_stage,
    JobStage.YOUTUBE_DOWNLOAD: _run_youtube_download_stage,
    JobStage.AUDIO_EXTRACT: _run_audio_extract_stage,
    JobStage.TRANSCRIBE: _run_transcribe_stage,
    JobStage.SIGNAL_EXTRACTION: _run_signal_extraction_stage,
    JobStage.CANDIDATE_SCORING: _run_candidate_scoring_stage,
}


def execute_job(db: Session, job_id: uuid.UUID, dispatch: Dispatcher | None = None) -> Job:
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

    next_stage = _NEXT_STAGE.get(job.stage)
    next_job_id: uuid.UUID | None = None
    if next_stage is not None:
        # enqueue_job commits, which also persists this job's completed
        # state in the same transaction — no separate commit needed.
        next_job = enqueue_job(db, stage=next_stage, source_video_id=job.source_video_id)
        next_job_id = next_job.id
    else:
        db.commit()

    db.refresh(job)

    if next_job_id is not None:
        (dispatch or _default_dispatch_job)(next_job_id)

    return job
