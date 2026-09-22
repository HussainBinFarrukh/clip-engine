# Clip Engine

Clip Engine is a planned monorepo content engine that turns authorized long-form video into platform-native clips with original commentary, human review, publishing, measurement, and a learning loop.

The build is task-driven. See `TASKS.md` for the ordered execution plan and `AGENTS.md` for standing engineering and content-policy rules.

## Current Task

Current task: T10 Candidate review UI. Phase 1 (ingest, transcribe) and T06-T09 of Phase 2 are done — see `docs/ROADMAP.md` for the full per-task status and `docs/DECISIONS.md` for the reasoning behind every deviation from `TASKS.md` (none silent).

Pipeline so far: create a project → add a source (local MP4 upload, or a YouTube URL downloaded server-side via `yt-dlp`; the app does not gate on source rights — see `docs/DECISIONS.md`) → `POST .../transcribe` (faster-whisper, word-level timestamps; one accept check unverified in this sandboxed environment, documented not skipped) → `POST .../extract-signals` (loudness, scene changes, pauses, speech rate, charted on Source Detail) → `POST .../score-candidates` (candidate windows per clip preset, deduped by heuristic score, top survivors scored by a Gemini-backed `LLMProvider` for hook/self-containedness/emotional-peak/quotability/score/reason, blended into a combined score, persisted as ranked `ClipCandidate` rows). Every stage after upload runs as an async job the request returns before, processed by the worker; failed jobs are retryable from Source Detail.

## Key Docs

- `docs/ARCHITECTURE.md`: Phase 1 architecture, schema, endpoints, UI pages, providers, job model, and local setup target.
- `docs/ROADMAP.md`: Task roadmap mirrored from `TASKS.md`.
- `docs/DECISIONS.md`: Architecture and product decisions.
- `docs/PLATFORMS.md`: Platform constraints and verification notes.

## Local Checks

The following non-Docker checks pass locally:

```powershell
npm --workspace @clip-engine/web test
npm --workspace @clip-engine/web run lint
.venv\Scripts\python.exe -m pytest apps\api\tests
.venv\Scripts\python.exe -m pytest workers\tests
.venv\Scripts\python.exe -m ruff check apps\api workers
```

Or run the helper script:

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ExecutionPolicy Bypass -File .\scripts\test-local.ps1
```

The media fixture can be regenerated with:

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ExecutionPolicy Bypass -File .\scripts\create-fixture.ps1
```

## Non-Negotiables

- Source is user-provided (local upload or YouTube URL); the app does not gate on rights, but the user is responsible for the legality of what they provide (see `docs/DECISIONS.md`).
- Original commentary is a first-class requirement.
- Human approval is required before publishing.
