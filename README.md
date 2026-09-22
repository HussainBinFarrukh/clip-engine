# Clip Engine

Clip Engine is a planned monorepo content engine that turns authorized long-form video into platform-native clips with original commentary, human review, publishing, measurement, and a learning loop.

The build is task-driven. See `TASKS.md` for the ordered execution plan and `AGENTS.md` for standing engineering and content-policy rules.

## Current Task

Current task: T04 Job system.

T03 (Upload, YouTube ingestion and storage) is done. Users can create a project, then add a source either by uploading an MP4 or by pasting a YouTube URL (downloaded server-side via `yt-dlp`). The app does not gate on source rights; users are responsible for the legality of what they provide (see `docs/DECISIONS.md`).

T02 (Scaffold) is done. The monorepo, Docker Compose stack (web, api, worker, postgres, redis), FastAPI health endpoint, Next.js shell, Dramatiq no-op worker with a Compose smoke producer, Alembic setup, tests, and a 45-second speech MP4 fixture are all in place. `docker compose up` serves the web page and API health check, the no-op job runs, and all test suites pass.

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

- Authorized sources only.
- No downloading YouTube audiovisual media.
- Original commentary is a first-class requirement.
- Human approval is required before publishing.
