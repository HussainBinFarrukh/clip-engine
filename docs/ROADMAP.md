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

- Current task: T04 Job system.
- 2026-09-22 scope change: the source-rights gate was removed at explicit product direction, and YouTube URL download is now in scope (via a `YouTubeSourceProvider`, e.g. `yt-dlp`). This knowingly runs against YouTube's Terms of Service; the user is responsible for source legality. See `docs/DECISIONS.md`.
- T03 is complete. `Project`, `SourceVideo` (no rights fields), and `MediaAsset` tables exist with an Alembic migration. `LocalDiskStorageProvider` stores originals; API responses never expose `storage_key` or filesystem paths. Upload endpoint validates MP4 format/size and extracts ffprobe metadata. `YtDlpYouTubeProvider` downloads a YouTube URL in a background task (verified against a real, very short public video) and stores it the same way as an upload. Web has Projects list/create, Project detail (add-source form: upload or YouTube URL) and Source detail (metadata + video player via a new streaming endpoint) pages. 12 API tests pass (including a fake-provider YouTube success/failure pair), plus web test/lint/format.
- T01 docs exist: `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/PLATFORMS.md`.
- T01 is complete.
- T02 is complete. The monorepo scaffold, Docker Compose stack (web, api, worker, postgres, redis), FastAPI health endpoint, Next.js shell, Dramatiq no-op worker with a Compose smoke producer, Alembic setup, lint/format/test tooling, and a 45-second speech MP4 fixture all exist and pass acceptance.
- T02 acceptance passed: Docker Desktop's WSL2 backend became available, `docker compose up` serves the web page and API health check, the no-op job runs (worker log shows `noop job: compose-smoke`), and the API, worker, and web test suites all pass in-container.
