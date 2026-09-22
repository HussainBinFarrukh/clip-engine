# Decisions

## 2026-09-22: Keep the First Slice Static

The current workstation stays dependency-free because Node, Python, Git, and ffmpeg are not available in the shell. This lets the project make usable progress while the future stack is documented for the next environment setup step.

## 2026-09-22: YouTube URLs Are References Only (Superseded)

Originally, YouTube URLs were exported as metadata/reference requests only, with no download of YouTube audiovisual content. This was superseded the same day — see "Remove Source Rights Gate; Allow YouTube Download" below.

## 2026-09-22: Rights and Commentary Are Required Gates (Superseded)

Originally, every render plan required a rights record in addition to commentary QA status, with rendering blocked when rights type or rights reference was missing. The rights-record requirement was superseded the same day — see "Remove Source Rights Gate; Allow YouTube Download" below. The commentary QA and human-approval gates are unaffected and remain required.

## 2026-09-22: Worker Shares the API's Code via a Read-Only Mount

T04 needed the Dramatiq worker to run real job stages (ffprobe, YouTube download) that read/write the same `SourceVideo`/`MediaAsset`/`Job` rows the API defines. Rather than duplicating the SQLAlchemy models and stage logic in the `workers/` package, the `worker` container mounts `apps/api` read-only and adds it to `PYTHONPATH`, so `app.models.*` and `app.services.jobs` import identically in both processes. Alembic migrations still live solely under `apps/api`; the worker never migrates, only reads/writes rows in tables the API has already migrated. The API only ever enqueues job messages (`run_job_stage.send(...)`) — the worker is the only process that executes a stage handler outside of tests. Both containers share the `storage_data` volume so a stage handler can read a file the API wrote.

## 2026-09-22: Remove Source Rights Gate; Allow YouTube Download

At explicit product direction, the app no longer collects or validates a `rights_type`/`rights_reference` on `SourceVideo`, and rendering/publishing is no longer blocked on a rights record. `SourceVideo` can be created from a local upload or a YouTube URL; YouTube URLs are downloaded locally (e.g. via `yt-dlp`) rather than kept as reference-only metadata.

This was raised as a legal/platform-policy concern before implementing: downloading YouTube content violates YouTube's Terms of Service and API Developer Policies, and republishing derivative clips of unrighted content carries real copyright exposure. The product owner explicitly accepted that risk and directed that the user, not the app, is responsible for having rights to whatever they provide. The app must not misrepresent this as sanctioned or safe, must not add features that make bulk/automated scraping easier, and must keep the still-mandatory commentary QA and human-approval-before-publishing gates intact — this decision narrows scope to the rights record only.

## 2026-09-22: Platform Limits Stay Configurable

Official platform requirements change. The app uses named presets and records platform targets, but final upload quota and publishing checks must be loaded from `docs/PLATFORMS.md` or provider configuration at runtime.

## 2026-09-22: YouTube API Upload Cost Needs Current Verification

Current Google documentation presents video upload quota differently than older 1,600-unit guidance. Treat quota cost and daily upload capacity as provider configuration, not a hardcoded business rule.

## 2026-09-22: Initialize Repository at T01

The workspace was not a Git repository, and Git was not initially installed. Git was installed with `winget`, the repository was initialized locally, and T01 is committed as the documentation baseline before the production scaffold begins.

## 2026-09-22: Use Docker-First Scaffold With Local Test Fallback

T02 is scaffolded for Docker Compose as the source of truth. Since Docker Desktop installation requires administrator elevation on this machine, local Node and Python toolchains were installed to validate the web, API, and worker tests until Docker is available.

## 2026-09-22: Add a Compose Worker Smoke Producer

The T02 Compose stack includes a one-shot `worker-smoke` service that enqueues a no-op Dramatiq message after Redis is healthy and the worker has started. This keeps the worker acceptance check observable during `docker compose up` without adding domain features.

## 2026-09-22: T02 Docker Acceptance Confirmed

Docker Desktop's WSL2 backend became available in this environment (no restart or further elevation needed beyond the earlier install). `docker compose up` was run from the existing checkout: `web` returns HTTP 200, `GET /health` on `api` returns `{"status":"ok",...}`, and the `worker` log shows the `worker-smoke` producer's no-op message was consumed (`noop job: compose-smoke`). The API (1 test), worker (3 tests), and web (1 test) suites, plus `ruff check` and `tsc --noEmit`, all pass when run inside their respective containers. T02 is marked done.
