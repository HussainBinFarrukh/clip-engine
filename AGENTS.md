# AGENTS.md — Clip Engine

Standing instructions for every session in this repository. Read this file, then `docs/ROADMAP.md` and `docs/DECISIONS.md`, before starting any task.

## Role

Act as technical lead and senior full-stack engineer on this project. Make routine engineering decisions yourself and record them briefly in `docs/DECISIONS.md`. Ask me only when a decision materially changes product direction, cost, legal exposure, or user experience. Point out architectural, security, cost, or platform-policy problems before implementing a request, and recommend the better approach when one exists.

## Product vision

A content engine that turns authorized long-form video into platform-native short and long-form clips with genuine original commentary, publishes them, measures performance, and uses the results to improve clip selection:

Source → transcribe → find moments → pair with reaction/commentary → transform → human review → publish → measure → learn

Build incrementally. Each phase must be working software. Design so later phases slot in without rewrites, but do not build future features before their phase.

## Non-negotiable content rules

1. **Source is user-provided, no rights gate in-app.** A `SourceVideo` is created either from a local upload or a YouTube URL. The app does not collect, validate, or block on rights metadata — the user is solely responsible for having the rights to any source they provide. This is a deliberate, explicit product decision (see `docs/DECISIONS.md`, 2026-09-22), not an oversight; do not reintroduce a rights gate without a matching decision entry.
2. **YouTube downloading is allowed, at the user's own risk.** YouTube URLs may be downloaded via a `YouTubeSourceProvider` (e.g. `yt-dlp`) for local processing. This runs against YouTube's Terms of Service and API Developer Policies as of 2026-09-21 — the user has accepted that risk for their own use. Never present this as officially sanctioned, never auto-publish YouTube-sourced footage without the human approval step in rule 4, and do not build features that make bulk/automated scraping easier than the user explicitly asking for one video at a time.
3. **Original commentary is core, not decoration.** Each clip is paired with a segment of my own recorded reaction or commentary. The reaction recording is a first-class entity. QA flags any clip whose commentary segment is missing, under 5 seconds, or has no speech.
4. **Human approval before publishing.** No clip is published without an explicit approval state set by a person.

## Platform constraints

Maintain `docs/PLATFORMS.md` as the single source of platform rules, each with a "last verified" date. Values below were verified 2026-09-21. Re-verify against official documentation before building anything that depends on them, and update the file when they change.

- YouTube Shorts: vertical or square, up to 3 minutes. From 2026-09-24, Shorts of 1–3 minutes with an active Content ID claim are no longer auto-blocked; globally blocked Shorts are not monetized.
- YouTube Data API: 10,000 quota units/day per Google Cloud project; an upload costs about 1,600 (about 6 uploads/day/project). Uploads from unverified apps are locked private.
- YouTube Partner Program: from 2027-02-01, new applicants need 8,000 watch hours or 20M Shorts views, and any channel needs 10M Shorts views per 90 days to keep receiving Shorts ad revenue.
- TikTok: Creator Rewards requires original content over 1 minute and names split screens and meaningless reactions as ineligible. Unaudited Content Posting API clients post private-only.
- Instagram: 50 API-published posts per rolling 24 hours per account.
- Recommended pacing: 2–4 posts per account per day, regardless of API ceilings.

## Clip length presets

Candidate generation targets presets, not one range. A strong moment may yield candidates for several presets.

| Preset | Duration | Aspect |
| --- | --- | --- |
| shorts_campaign | 15–60 s | 9:16 |
| shorts_long | 60–180 s | 9:16 |
| tiktok_rewards | 61–180 s | 9:16 |
| longform | 8–20 min | 16:9 |

## Architecture principles

- **Monorepo:** `apps/web` (Next.js, TypeScript, Tailwind), `apps/api` (FastAPI), `workers/` (Python), `packages/` for shared types, `docs/`.
- **Data and queue:** PostgreSQL via SQLAlchemy and Alembic. Redis with Dramatiq for background jobs.
- **Local development:** Docker Compose for all services.
- **Provider interfaces:** `SourceProvider`, `StorageProvider`, `Transcriber`, `LLMProvider`, and later `Publisher` and `AnalyticsProvider`. No provider-specific logic outside its adapter.
  - Storage starts as local disk; S3 is a later adapter.
  - LLMs are called only through `LLMProvider`, with structured JSON output validated by Pydantic.
- **Transcription:** faster-whisper, large-v3 on CUDA when available, with a smaller model on CPU. Word-level timestamps are required. Plan for diarization (whisperX) later.
- **Pipeline stages:** each stage is idempotent, persists its output and job state before the next stage starts, and is retryable. Job states are queued, processing, completed, and failed, with progress where practical, plus a stored error.
- **Storage layout:** originals are never modified. Originals and derived assets are logically separated. Use generated asset IDs; never trust filenames or expose filesystem paths.
- **Learning loop:** every clip candidate stores its full feature vector and scoring inputs at generation time (hook type, duration, energy, transcript features, preset, model and prompt version). Performance metrics will later join on candidate ID.
- **Scores:** treat them as an internal ranking signal, never presented as a virality prediction.
- **Secrets:** environment variables only; API keys server-side.
- **Uploads:** validate format and size, with limits configurable.

## Domain model (grow into it; create tables only when their phase needs them)

User, Workspace, Project, SourceVideo, MediaAsset, Transcript, TranscriptWord, TranscriptSegment, ReactionSession, ReactionSegment, ClipCandidate (with features), Clip, RenderJob, RenderedAsset, PlatformAccount, PublishJob, SocialPost, PerformanceMetric, AIAnalysis.

## Definition of done for any task

- `docker compose up` runs the full stack from a clean checkout.
- Automated tests cover the new logic, using the small media fixture in `tests/fixtures/`.
- No mocks hide unfinished core functionality; anything incomplete is marked clearly in code and in `docs/ROADMAP.md`.
- The relevant docs are updated: `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/PLATFORMS.md` where relevant.
- End the task with a short summary: what was built, decisions made, current limitations, and the recommended next step.

## Roadmap outline

1. **Ingest and transcribe:** upload, storage, queue, audio extraction, word-level transcript, transcript view.
2. **Candidate generation:** heuristic signals (audio energy, scene changes, pauses, sentence boundaries), LLM scoring over transcript windows, presets, stored features, candidate list UI with reasons.
3. **Render:** cut, reframe to 9:16, word-highlighted burned-in captions, timestamp adjustment, MP4 export.
4. **Reaction pairing:** upload a reaction session, align segments to clips by audio marker, composed layouts (stacked or picture-in-picture), audio ducking, QA gates.
5. **Review and publish:** approval queue, scheduler with per-platform pacing and quota enforcement, YouTube first, then TikTok and Instagram.
6. **Measure and learn:** analytics pulls at 24 h, 72 h, and 7 d; joined performance table; weekly rubric and prompt revision from top and bottom performers.
