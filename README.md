# Clip Engine

Clip Engine is a planned monorepo content engine that turns authorized long-form video into platform-native clips with original commentary, human review, publishing, measurement, and a learning loop.

The build is task-driven. See `TASKS.md` for the ordered execution plan and `AGENTS.md` for standing engineering and content-policy rules.

## Current Task

Current task: T01 Architecture and docs.

T01 is documentation-only. The production stack begins in T02 with the monorepo scaffold, Docker Compose, FastAPI, Next.js, worker, Alembic, test tooling, and media fixture.

## Key Docs

- `docs/ARCHITECTURE.md`: Phase 1 architecture, schema, endpoints, UI pages, providers, job model, and local setup target.
- `docs/ROADMAP.md`: Task roadmap mirrored from `TASKS.md`.
- `docs/DECISIONS.md`: Architecture and product decisions.
- `docs/PLATFORMS.md`: Platform constraints and verification notes.

## Non-Negotiables

- Authorized sources only.
- No downloading YouTube audiovisual media.
- Original commentary is a first-class requirement.
- Human approval is required before publishing.
