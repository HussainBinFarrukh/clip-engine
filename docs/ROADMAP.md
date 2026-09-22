# Roadmap

This roadmap mirrors `TASKS.md`. Build one task at a time, in order.

## Phase 1: Ingest and Transcribe

- T01: Architecture and docs.
- T02: Scaffold monorepo, Docker Compose, health endpoint, web shell, worker, Alembic, test tooling, fixture.
- T03: Upload, YouTube ingestion, and storage.
- T04: Job system.
- T05: Audio extraction and transcription.

## Phase 2: Candidate Generation

- T06: Signal extraction.
- T07: Candidate windows.
- T08: LLM provider.
- T09: Scoring, ranking, and features.
- T10: Candidate review UI.

## Phase 3: Render

- T11: Basic render.
- T12: Face-tracked reframe.
- T13: Captions and audio finishing.

## Phase 4: Reaction Pairing

- T14: Reaction sessions.
- T15: Reaction alignment.
- T16: Composed layouts.
- T17: QA gates and approval states.

## Phase 5: Review and Publish

- T18: Review queue and metadata.
- T19: Campaign tracking.
- T20: YouTube publisher and scheduler.
- T21: TikTok and Instagram publishers.

## Phase 6: Measure and Learn

- T22: Analytics ingestion.
- T23: Performance dashboard and rubric loop.

## Current Status

- Current task: T05 Audio extraction and transcription.
- 2026-09-22 scope change: the source-rights gate was removed at explicit product direction, and YouTube URL download is now in scope (via a `YouTubeSourceProvider`, e.g. `yt-dlp`). This knowingly runs against YouTube's Terms of Service; the user is responsible for source legality. See `docs/DECISIONS.md`.
- T03 is complete. `Project`, `SourceVideo` (no rights fields), and `MediaAsset` tables exist with an Alembic migration. `LocalDiskStorageProvider` stores originals; API responses never expose `storage_key` or filesystem paths.
- T04 is complete. A generic `Job` table (stage, state, progress, attempts, error fields, input/output JSON) backs a stage-runner (`app.services.jobs.execute_job`) that persists the "processing" state and incremented attempt count before running a stage, and rolls back partial writes on failure so a retry starts clean. The upload and YouTube-download flows from T03 were refactored onto this system: uploading now stores the file synchronously but runs ffprobe as an `upload_metadata` job, and both endpoints return a response snapshot taken *before* dispatch, so the "API returns before any stage runs" contract holds regardless of dispatch timing. `POST /jobs/{id}/retry` reruns a failed job; `GET /jobs/{id}` and `GET /projects/{id}/jobs` expose status. The worker container now shares the API's code (read-only mount + `PYTHONPATH`, see `docs/DECISIONS.md`) so `run_job_stage` executes the same stage handlers the API enqueues — verified against the real Redis/worker pipeline, including a genuine YouTube-download failure and retry. A `test_stage` (fails a configurable number of attempts, then succeeds) demonstrates the retry mechanism deterministically in `apps/api/tests/test_jobs.py`. Web's Source Detail page polls `GET /projects/{id}/jobs` every 3s and shows a Retry button on failed jobs. 16 API tests + 3 worker tests pass, plus web test/lint/format.
- T01 docs exist: `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/PLATFORMS.md`.
- T01 is complete.
- T02 is complete. The monorepo scaffold, Docker Compose stack (web, api, worker, postgres, redis), FastAPI health endpoint, Next.js shell, Dramatiq no-op worker with a Compose smoke producer, Alembic setup, lint/format/test tooling, and a 45-second speech MP4 fixture all exist and pass acceptance.
- T02 acceptance passed: Docker Desktop's WSL2 backend became available, `docker compose up` serves the web page and API health check, the no-op job runs (worker log shows `noop job: compose-smoke`), and the API, worker, and web test suites all pass in-container.
