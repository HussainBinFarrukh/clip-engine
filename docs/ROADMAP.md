# Roadmap

This roadmap mirrors `TASKS.md`. Build one task at a time, in order.

## To Revisit

Known gaps worth a deliberate second pass, not silently dropped:

- **T05 word-timestamp precision (~100ms accept bar unmet).** No GPU here → `faster-whisper` runs `tiny` on CPU, not `large-v3`. The synthetic SAPI test fixture also has unnaturally large inter-word pauses that are out-of-distribution for Whisper's alignment (confirmed by investigation, not assumed) — see `docs/DECISIONS.md`, "Fixture Gets Real Ground-Truth Word Timestamps...". **Before T13** (captions need tight audio sync): swap the fixture for a real recorded human-speech sample, and re-test against `large-v3` once GPU is available (or accept `tiny`'s precision as a deliberate product tradeoff and document that instead).
- **T06 signals chart placement.** Built on Source Detail, not the literal "project page" TASKS.md names — a signal series is per-source, and Project Detail lists multiple sources with none selected. If "project page" was intentional (e.g. a cross-source overview), that's a different, bigger feature — revisit if it turns out to matter. See `docs/DECISIONS.md`.
- **T09 real end-to-end scoring run.** The full real-API pipeline (upload → transcribe → signals → score) is proven correct piece-by-piece against the live Gemini API (T08's simple real call passed; the full-pipeline real call reached Google's servers and got real, if capacity-limited, responses), but a genuine `503`/`429` from Google's side during testing means the full pipeline's *success* path hasn't been observed end-to-end against the live API in this session — only via the fake-provider tests. Re-run `test_candidate_scoring_stage.py::test_real_scoring_produces_plausible_ranked_candidates` once the API isn't under high demand (it self-skips otherwise, doesn't fail) to get that final real confirmation.

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

- Current task: T11 Basic render (Phase 3). Phase 2 (Candidate Generation, T06-T10) is complete.
- T10 is complete. `ClipCandidate` gained `review_status` (`pending`/`accepted`/`rejected`) and `transcript_excerpt`. `PATCH /projects/{id}/sources/{id}/candidates/{id}` updates either or both; a time adjustment is independently re-validated server-side (must land on a real sentence boundary, duration must still fit the preset) rather than trusting the client, even though the web UI's `<select>` dropdowns (populated only from real transcript boundaries) can't construct an invalid request in the first place. `GET .../candidates/{id}/thumbnail` grabs a JPEG frame via ffmpeg on demand (not persisted, so it can never go stale after a time edit). Source Detail's new Candidates panel: thumbnail, preset, review status, combined score, excerpt, reason, quotable line, a Preview button (seeks the shared video player, now shared code between Transcript and Candidates panels via `lib/video-player.ts`), and Accept/Reject. Verified real end-to-end against the actual pipeline (upload → transcribe → signals → score) with real ffmpeg thumbnail extraction and real PATCH persistence, confirmed visible in the rendered page. 54 API tests + 3 worker tests pass (2 real-Gemini tests still skip on the live rate-limit/capacity issue from T09 — unrelated to T10, not yet cleared).
- T09 is complete. `app/services/candidate_scoring.py` (pure, tested): heuristic features from T06 `Signal` series per window (avg loudness, pause ratio, avg speech rate, scene-change count), a 0-100 `heuristic_score`, and NMS-based `deduplicate_windows` capping LLM calls to 3 per preset. The `candidate_scoring` job stage scores survivors with `run_llm_call` (prompt `clip_scoring`, schema `hook_line`/`self_contained`/`emotional_peak`/`quotable_line`/`score`/`reason`), blends `combined_score = 0.3*heuristic + 0.7*llm` (both weightings explicit placeholders), and persists `ClipCandidate` rows with the full feature vector, model, and prompt version. `POST .../score-candidates` → `GET .../candidates` (ranked by `combined_score`). Re-scoring the same prompt version replaces its rows (idempotent retry); a new prompt version adds alongside old rows, not over them — verified with a genuine second prompt file (`clip_scoring/v2.txt`), not a fake version number. Testing against the live API surfaced a real, reproducible Gemini `503`/`429` capacity issue (not a bug); fixed with HTTP-layer retry-with-backoff, and real-API tests now skip gracefully on that specific signature instead of failing — see `docs/DECISIONS.md` and "To Revisit" above. 50 API tests + 3 worker tests pass (2 real-API tests currently skip due to that live capacity issue; re-run when available).
- T08 is complete. `app/services/llm_provider.py`: `LLMProvider` interface, `GeminiProvider` hosted adapter (chosen at explicit product direction — Gemini now, OpenAI later; Ollama skipped, unrequested — see `docs/DECISIONS.md`), `generate_structured()` (provider-agnostic JSON-vs-Pydantic-schema validation with retry-then-clean-failure), and `run_llm_call()` (DB wrapper that records every attempt, success or failure, as an `AIAnalysis` row). Prompts are versioned files (`app/prompts/{name}/v{n}.txt`); T08 ships one demo prompt to exercise the infrastructure, not a real scoring prompt (that's T09). Real `GEMINI_API_KEY` provided and verified with a live call before building on it; found and fixed two real issues doing so — the model's default "thinking" mode adds pure overhead for structured output (disabled), and this environment's network needed a 120s timeout, not 60s. 38 API tests pass (includes one live Gemini call, skipped automatically if no key is configured).
- T07 is complete. `app/services/candidate_windows.py` generates every sentence-boundary-snapped window, per preset (`app/services/clip_presets.py`, mirroring `AGENTS.md`'s table), whose duration fits the preset's bounds; overlapping windows from different start sentences are kept. Pure library code, no DB table or API endpoint — persistence waits for T09's `ClipCandidate` (see `docs/DECISIONS.md`). Verified for all four presets via a synthetic multi-minute sentence list (the real fixture is too short for anything past `shorts_campaign`), and "never cuts a sentence" verified both structurally and, against the real fixture's transcript, at the word level. 30 API tests pass.
- T06 is complete. `Signal` rows (one per `(source_video, signal_type)`, `points_json` time series) store loudness/RMS (stdlib `wave` module, 200ms windows, dBFS), scene changes (PySceneDetect `ContentDetector`, verified against both a static-background clip — 0 cuts — and a synthetic 2-scene clip — 1 correctly-placed cut), pauses (≥300ms gaps between transcript words), and speech rate (words/minute per transcript segment). `POST /projects/{id}/sources/{id}/extract-signals` enqueues `signal_extraction`, requires the source to be `ready` (transcript exists); re-extracting deletes and replaces the four series (no duplicates, verified). Sentence boundaries are the `speech_rate` points' own timestamps, not a separate series. Source Detail shows a small-multiples SVG timeline (shared time axis, dataviz-skill-validated dark-mode palette, hover crosshair) instead of the literal "project page" TASKS.md names — documented deviation, see `docs/DECISIONS.md`. 24 API tests + 3 worker tests pass.
- 2026-09-22 scope change: the source-rights gate was removed at explicit product direction, and YouTube URL download is now in scope (via a `YouTubeSourceProvider`, e.g. `yt-dlp`). This knowingly runs against YouTube's Terms of Service; the user is responsible for source legality. See `docs/DECISIONS.md`.
- T03 is complete. `Project`, `SourceVideo` (no rights fields), and `MediaAsset` tables exist with an Alembic migration. `LocalDiskStorageProvider` stores originals; API responses never expose `storage_key` or filesystem paths.
- T04 is complete. A generic `Job` table (stage, state, progress, attempts, error fields, input/output JSON) backs a stage-runner (`app.services.jobs.execute_job`) that persists the "processing" state and incremented attempt count before running a stage, and rolls back partial writes on failure so a retry starts clean. The upload and YouTube-download flows from T03 were refactored onto this system: uploading now stores the file synchronously but runs ffprobe as an `upload_metadata` job, and both endpoints return a response snapshot taken *before* dispatch, so the "API returns before any stage runs" contract holds regardless of dispatch timing. `POST /jobs/{id}/retry` reruns a failed job; `GET /jobs/{id}` and `GET /projects/{id}/jobs` expose status. The worker container now shares the API's code (read-only mount + `PYTHONPATH`, see `docs/DECISIONS.md`) so `run_job_stage` executes the same stage handlers the API enqueues — verified against the real Redis/worker pipeline, including a genuine YouTube-download failure and retry. A `test_stage` (fails a configurable number of attempts, then succeeds) demonstrates the retry mechanism deterministically in `apps/api/tests/test_jobs.py`. Web's Source Detail page polls `GET /projects/{id}/jobs` every 3s and shows a Retry button on failed jobs. 16 API tests + 3 worker tests pass, plus web test/lint/format.
- T05 is complete, with one accept check unverified (documented, not silently skipped). `audio_extract` (ffmpeg → 16kHz mono WAV) and `transcribe` (faster-whisper, word timestamps on) are job stages that auto-chain: `POST /projects/{id}/sources/{id}/transcribe` enqueues `audio_extract`, which enqueues `transcribe` on success. `Transcript`/`TranscriptSegment`/`TranscriptWord` tables store results; re-transcribing deletes and replaces the prior transcript (no duplicates, verified). `GET /sources/{id}/transcript` serves it; the Source Detail page shows clickable, player-seeking word timestamps once ready. The "~100ms" word-timestamp accept bar could not be verified in this environment — no GPU for `large-v3`, and the available TTS test fixture has unnaturally large inter-word pauses that are out-of-distribution for Whisper's alignment (confirmed by direct investigation). Tests instead verify transcript text accuracy against a real ground-truth fixture (`tests/fixtures/speech_45s.words.json`, captured from the synthesizer's own word-boundary events) and structural correctness of stored timestamps. See `docs/DECISIONS.md` for the full investigation and what to re-verify before relying on tight sync (T13 captions). 20 API tests + 3 worker tests pass.
- T01 docs exist: `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/PLATFORMS.md`.
- T01 is complete.
- T02 is complete. The monorepo scaffold, Docker Compose stack (web, api, worker, postgres, redis), FastAPI health endpoint, Next.js shell, Dramatiq no-op worker with a Compose smoke producer, Alembic setup, lint/format/test tooling, and a 45-second speech MP4 fixture all exist and pass acceptance.
- T02 acceptance passed: Docker Desktop's WSL2 backend became available, `docker compose up` serves the web page and API health check, the no-op job runs (worker log shows `noop job: compose-smoke`), and the API, worker, and web test suites all pass in-container.
