# Decisions

## 2026-09-22: Keep the First Slice Static

The current workstation stays dependency-free because Node, Python, Git, and ffmpeg are not available in the shell. This lets the project make usable progress while the future stack is documented for the next environment setup step.

## 2026-09-22: YouTube URLs Are References Only

YouTube URLs are exported as metadata/reference requests only. The product must not download or store YouTube audiovisual content without explicit platform approval. Source media for actual clipping starts with local authorized uploads.

## 2026-09-22: Rights and Commentary Are Required Gates

Every render plan carries a rights record and commentary QA status. Backend rendering must block when rights type, rights reference, or commentary is missing. Publishing remains blocked until a human approval state is set.

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
