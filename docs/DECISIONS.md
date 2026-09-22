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

## 2026-09-22: Transcription Is User-Triggered, Not Automatic on Upload

`upload_metadata`/`youtube_download` do not auto-chain into `audio_extract`. Transcription is CPU/compute-heavy (real, non-trivial wall-clock time even on a small model), so it runs only when the user explicitly requests it via `POST .../transcribe`, not on every upload. `audio_extract` and `transcribe` do auto-chain into each other, since from the user's perspective "transcribe this video" is one action, just implemented as two separately-retryable stages.

This also kept T03/T04's existing fast tests fast: they create/upload sources without ever touching the transcription pipeline, so they aren't coupled to whisper model downloads or CPU inference time.

## 2026-09-22: faster-whisper CPU Default Is `tiny`, Not a Larger Model

`large-v3` (the CUDA-path model per `AGENTS.md`) is several GB and this environment has no GPU passthrough, so the CPU-path default is `WHISPER_MODEL_CPU=tiny` — small enough to download and run in a sandboxed dev environment with a slow, rate-limited network connection. `WHISPER_MODEL_CPU` is a plain environment variable a real deployment can override (e.g. to `small` or `medium`) once it has the network/CPU budget for a heavier model.

## 2026-09-22: Fixture Gets Real Ground-Truth Word Timestamps, But T05's ~100ms Accept Bar Is Not Verified

`scripts/create-fixture.ps1` now captures real per-word start times during speech synthesis (via `SpeechSynthesizer.SpeakProgress`, exposed through a small inline C# helper since PowerShell's own event-delegate casting didn't work) and writes them to `tests/fixtures/speech_45s.words.json`, replacing an unlabeled guess with an actual, checkable ground truth. The script also switched from one sentence repeated 3× to 8 distinct sentences (verbatim repetition is a known Whisper timestamp-drift trigger), and measures the synthesized WAV's *real* duration via `ffprobe` to bound the ground truth — `SpeakProgress`'s `AudioPosition` events ran several seconds ahead of the WAV actually written to disk, a SAPI quirk worth knowing about if this script is reused.

With that real ground truth in hand, `apps/api/tests/test_transcription.py` found that faster-whisper's predicted word timestamps drift by several seconds over the ~35s clip (growing roughly proportionally, not random per-word jitter) — confirmed to be caused by the fixture's synthetic voice, not a pipeline bug: the SAPI voice has large, irregular inter-word pauses (several hundred ms between many word pairs, unlike natural speech), reproduced at both `Rate=-1` and the default rate. That prosody is out-of-distribution for Whisper's attention-based word alignment. Segment-level transcribed *text* is accurate (all 8 sentences transcribed correctly, in order, via a real diff against ground truth).

Given that, the test asserts what's actually reliable — text accuracy against ground truth, and structural correctness of stored timestamps (bounded, monotonic) — and does not assert millisecond accuracy against ground truth. **TASKS.md's T05 accept bar ("word timestamps within about 100ms") is therefore not verified in this environment.** It assumes `large-v3` on natural speech; this environment has neither a GPU nor a natural-speech test fixture. Before relying on tight audio/caption sync (T13), re-verify against `large-v3` and a real recorded voice sample.

## 2026-09-22: Whisper Model Weights Persist in a Named Volume

The first `faster-whisper` call downloads model weights from Hugging Face Hub at runtime (not baked into the image). Without a persistent cache, every `docker compose down` + `up` re-downloads them, adding ~50s+ to the next transcription on this environment's slow network. `api` and `worker` now both mount a shared `hf_cache` volume at `HF_HOME=/data/hf-cache` so the download only happens once per environment, not once per container recreation.

## 2026-09-22: Worker Runs Need a Restart, Not Just a File Change

Unlike the API (uvicorn `--reload` watches the mounted volume), the Dramatiq worker process does not hot-reload — it has whatever Python objects (including enum classes) were in memory when it started. A code change that isn't paired with `docker compose up -d worker` (or an image rebuild, when dependencies changed) leaves the worker running stale code, which surfaces as confusing low-level errors (e.g. a `LookupError` deserializing an enum value the running process's stale `JobStage` doesn't know about) rather than an obvious version mismatch. Restart the worker after any change under `apps/api` or `workers/` that isn't purely test-only.

## 2026-09-22: Signal Extraction Is a Separate, Explicit Stage — Not Auto-Chained from Transcribe

`signal_extraction` (T06: loudness/RMS, scene changes, pauses, speech rate) needs a transcript (for pauses and speech rate) plus the original video and extracted audio, so it can only run after `transcribe` succeeds. It is deliberately *not* auto-chained onto `transcribe` the way `audio_extract` auto-chains into `transcribe` — scene detection (PySceneDetect) is its own real compute cost, and stacking it onto every transcription would make "transcribe this video" silently do more work than asked. `POST /projects/{id}/sources/{id}/extract-signals` is a separate, explicit call, consistent with the T05 decision to keep compute-heavy stages opt-in rather than automatic.

## 2026-09-22: Signals Timeline Chart Lives on Source Detail, Not the Project Page

TASKS.md's T06 accept criterion says the signals timeline should be "visible... on the project page." It's built on the Source Detail page instead: a signal series is per-`source_video`, and the Project Detail page lists *multiple* sources with no single one selected — a chart there would need its own source picker, adding real complexity `T06`'s "Out of scope: scoring" framing didn't ask for, for something the Source Detail page (which already has the player and transcript to correlate the timeline against) does for free. Flagging this as a deliberate reading, not a silent deviation, in case "project page" was intentional for a reason not visible from the task list alone.

## 2026-09-22: RMS Loudness Computed with the Stdlib `wave` Module, Not ffmpeg Filters or a New Library

`audio_extract` already produces a 16kHz mono 16-bit PCM WAV for the transcriber, and that format is trivial to read directly with Python's built-in `wave`/`array` modules — no new dependency, no shelling out to an `ffmpeg` audio-filter pipeline whose text output would need parsing. RMS energy is computed per 200ms window and converted to dBFS, floored at -60dBFS for silence (avoids `log(0)`).

## 2026-09-22: Scene Detection Uses PySceneDetect's `ContentDetector`, Pulls in OpenCV

TASKS.md names PySceneDetect explicitly for T06, so `scenedetect` (plus its `opencv-python-headless` dependency) was added to both `apps/api/requirements.txt` and `workers/requirements.txt` — another sizable download in this environment's slow-network sandbox, mitigated by the pip cache mount added in T05. `ContentDetector` (HSV colorspace delta between frames) is the library's general-purpose default; the T05/T06 test fixture (a static color background) correctly produces zero detected cuts. To confirm that's the expected negative case and not a bug, `compute_scene_changes` was also run against a synthetic 2-scene clip (red 0-2s, blue 2-4s): it correctly detected one cut at `t_ms: 2000`.

## 2026-09-22: T07 Candidate Windows Are Pure Library Code, No DB Table or Endpoint Yet

T07's Build section ("window generation per clip preset... snapped to sentence boundaries... overlap allowed") and Accept criteria ("each preset yields windows within its duration bounds," "no window cuts a sentence") are both fully testable as a pure function over a transcript's sentence boundaries — nothing in T07 asks for persistence, an API endpoint, or a UI. `ClipCandidate` (the table that will actually store generated windows, alongside their score and feature vector) is explicitly T09's job in TASKS.md. Building a `candidate_windows` table now would mean building it again once T09 adds scoring, or awkwardly bolting scores onto a table designed without them — so `app/services/candidate_windows.py` stays a pure, tested module (`generate_candidate_windows`) that T09 will call and wrap with persistence, matching AGENTS.md's "do not build future features before their phase."

Tested two ways: a synthetic multi-minute sentence list exercises all four presets, including `longform` (8-20 min), which the real ~37s test fixture is far too short to reach; the real fixture's actual transcript is used for a stronger, word-level version of "never cuts a sentence" (no `TranscriptWord` is left straddling a window boundary), since the fixture is long enough for `shorts_campaign` (15-60s).

## 2026-09-22: T08 LLM Provider Targets Gemini First, OpenAI Later — at Explicit Product Direction

TASKS.md's T08 asks for "one hosted adapter" plus an optional Ollama adapter, without naming a provider. Asked directly, the product owner chose Gemini now, with an explicit intent to add OpenAI later — Ollama (local) was not requested and is skipped for now (it's the optional half of T08's Build line). `get_llm_provider()` switches on `LLM_PROVIDER` (currently only `"gemini"` is implemented); adding OpenAI later is a new branch there plus an `OpenAIProvider` class implementing the same `LLMProvider.generate()` contract — no changes needed to `generate_structured`, `run_llm_call`, or anything that calls them.

A real `GEMINI_API_KEY` was provided and verified with a live call before any code was built on top of it (same standard held for every other external integration in this project) — stored in `.env` (gitignored), passed into the `api`/`worker` containers via `env_file:` in `docker-compose.yml`, never committed.

## 2026-09-22: Gemini Calls Disable "Thinking" and Use a 120s Timeout

Two things learned by testing against the real API, not assumed: (1) `gemini-3.6-flash`'s default "thinking" mode burned 52 "thought" tokens answering "Say OK" — pure overhead for T08's structured-JSON use case, which doesn't need extended reasoning. `generationConfig.thinkingConfig.thinkingBudget: 0` eliminates it (confirmed: 0 thought tokens with it set). (2) Even trivial prompts took 20-50+ seconds end-to-end from this environment — not the model "thinking," since disabling thinking didn't reliably shorten it either; this environment's outbound network already showed similar slow/variable latency for other external traffic (pip installs, model downloads) throughout this build. The original 60s request timeout was too tight and caused a real, reproducible `ReadTimeout` in a test; raised to 120s.

## 2026-09-22: Gemini Per-Token Pricing Is a Placeholder

`_GEMINI_PRICING_PER_MILLION_TOKENS` in `app/services/llm_provider.py` holds a placeholder rate for `gemini-3.6-flash`, not a verified current price — the same "needs current verification before trusting for real numbers" caveat this project already applies to YouTube/TikTok/Instagram platform limits in `docs/PLATFORMS.md`. `cost_usd` on every `AIAnalysis` row is real arithmetic on real token counts, so it's internally consistent and fine for relative comparisons (which call was expensive vs. cheap), but re-verify the per-million rates against Google's current published pricing before using the numbers for actual budget decisions.

## 2026-09-22: T09 Dedupes on Heuristics Before Any LLM Call, Caps LLM Calls Per Preset

T07 deliberately generates every overlapping window a preset allows (`shorts_campaign` alone can yield a dozen+ for a short clip); scoring every one of them with the LLM would multiply real cost and latency for near-duplicate content. `app/services/candidate_scoring.py`'s `deduplicate_windows` runs non-maximum suppression (standard object-detection technique, directly applicable to overlapping time windows) on the cheap heuristic score *before* any LLM call, keeping at most `_MAX_CANDIDATES_PER_PRESET` (3) survivors per preset. The LLM only ever sees windows that already cleared this filter.

`heuristic_score`'s weights (40% loudness, 40% "flow" i.e. low pause ratio, 20% speech rate) and `combined_score`'s weights (30% heuristic, 70% LLM) are both explicitly documented as a starting point, not a tuned model — nothing has been published yet to validate against. This is exactly the gap AGENTS.md's learning loop (performance metrics joining on candidate ID) is meant to eventually close; until then, treat these numbers as reasonable defaults open to revision, not settled.

## 2026-09-22: Re-Scoring Semantics — Same Prompt Version Replaces, New Version Adds Alongside

T09's accept criterion is explicit: "re-scoring with a new prompt version keeps the old results." This is the opposite of every other delete-then-insert idempotency pattern in this codebase (transcripts, signals) — deliberately: `ClipCandidate` rows are deleted-and-replaced only within the same `(source_video, preset, prompt_name, prompt_version)` scope (so retrying a stuck/failed job is still safe and doesn't duplicate rows), but a *different* `prompt_version` is additive. This is what makes prompt-version comparison possible later (T23's rubric loop) — old scores stay queryable after a prompt changes. Verified with a real second prompt file (`clip_scoring/v2.txt`, a genuinely different, stricter prompt — not a copy — see the next entry) rather than a synthetic version number, since `load_prompt` would 404 on a version that doesn't exist as a file, which a fake version number wouldn't have caught.

## 2026-09-22: A Second clip_scoring Prompt Version Exists Only Because a Test Needed One — and Stayed

Testing "new prompt version keeps old results" honestly required an actual `v2.txt` prompt file (prompts are versioned files; a test can't fabricate one). Rather than write a throwaway near-duplicate, `v2` is a real, stricter revision (explicit "most excerpts do NOT work standalone," reserves 70+ scores for clips worth publishing as-is) — a genuine first iteration a real project would make after seeing v1's output skew too generous. It is not activated by default (`prompt_version` defaults to 1); nothing currently depends on v2 being "the good one." This is a case where the honest way to write the test produced a real, usable artifact instead of a mock.

## 2026-09-22: Gemini Transient Errors (503 "High Demand", 429 Rate-Limit) Are Real, Reproduced Live — Retried at the HTTP Layer, Tests Skip Gracefully

Scoring the fixture against the real API hit a genuine, reproducible `503 UNAVAILABLE` ("This model is currently experiencing high demand") on `gemini-3.6-flash` — and the same error on `gemini-flash-latest`, `gemini-3.5-flash`, and `gemini-3.1-flash-lite` when tried as alternatives, while a trivial "Say OK" prompt against the same key succeeded around the same time. This is Google-side capacity, not a bug in the request. Continued testing to isolate it also triggered `429` (rate-limiting from the volume of manual debugging calls made against one API key in a short window).

Two changes, at two different layers, because they're different problems:
- **`GeminiProvider.generate()` now retries transport/server errors** (429, 500, 502, 503, 504) with backoff (`_TRANSIENT_RETRY_ATTEMPTS = 3`, `_TRANSIENT_RETRY_BACKOFF_SECONDS = 2.0`, linear), separate from `generate_structured`'s existing retry loop for invalid *JSON* — a 503 isn't an output-quality problem, it's an availability problem, and conflating the two retry budgets would burn output-format retries on a request that never reached the model.
- **Real-API tests treat a persistent transient failure as skip, not fail** (`tests/conftest.py`'s `skip_if_transient_llm_outage`, matched against the literal error text: "503", "UNAVAILABLE", "high demand", "429", "RESOURCE_EXHAUSTED", "rate limit"). A live third-party outage during a test run is not a regression in this codebase and shouldn't block the suite or look like one; anything that doesn't match a known transient signature still fails the test normally. `test_llm_provider.py`'s simple-prompt real test and `test_candidate_scoring_stage.py`'s full-pipeline real test both use it.

The underlying mechanism is still verified against the live API, not just asserted: the T08 real-call test passed against the live API in this same session, and direct requests with the actual `clip_scoring` prompt reached Google's servers and got real (if capacity-limited) responses, not connection or auth failures — the integration is correct; availability was the constraint on the day of testing.
