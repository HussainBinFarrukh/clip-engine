# Roadmap

This roadmap mirrors `TASKS.md`. Build one task at a time, in order.

## Phase 1: Ingest and Transcribe

- T01: Architecture and docs.
- T02: Scaffold monorepo, Docker Compose, health endpoint, web shell, worker, Alembic, test tooling, fixture.
- T03: Upload, rights validation, and storage.
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

- Current task: T02 Scaffold.
- T01 docs exist: `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/PLATFORMS.md`.
- T01 is complete.
- T02 has not started. The monorepo, Docker Compose stack, backend services, and tests are not implemented yet.
