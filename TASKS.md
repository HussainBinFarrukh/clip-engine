# TASKS.md — Clip Engine build plan

Ordered task list for the whole build. `AGENTS.md` holds the standing rules; this file holds the work.

## Execution protocol (for Codex)

1. Work on exactly one task at a time, in order: the first task whose status is not `done`.
2. Before starting, re-read `AGENTS.md`, this task, and `docs/DECISIONS.md`.
3. Implement only what the task's **Build** section lists. Anything under **Out of scope** stays out, even if it looks easy.
4. Run every check in **Accept**. Do not mark the task done until all pass. If a check cannot pass, stop and explain why.
5. Set the task's status to `done`, update `docs/ROADMAP.md` and `docs/DECISIONS.md`, and commit with the message `T##: <title>`.
6. Stop. Summarize what was built, decisions made, limitations, and anything learned that should change a later task. Wait for "next" before starting the following task.
7. If what you learn makes a later task wrong or unnecessary, propose an edit to this file in your summary. Do not silently deviate from it.

## External prerequisites (done by me, in parallel, not by Codex)

- [ ] Create a Google Cloud project, enable YouTube Data API v3 and YouTube Analytics API, configure the OAuth consent screen, and submit the app for verification and a quota increase (needed by T20; approval takes weeks).
- [ ] Register a TikTok developer app and apply for the Content Posting API audit (needed by T21).
- [ ] Set up an Instagram Professional account linked to a Facebook Page, plus a Meta developer app (needed by T21).
- [ ] Get an LLM API key (needed by T08).

---

## Phase 1: Ingest and transcribe

### T01: Architecture and docs · status: done
**Build:**
- `docs/ARCHITECTURE.md`: repo structure, a Mermaid component diagram, the Phase 1 schema, the job state machine, the provider interfaces, the Phase 1 API endpoints and UI pages, and local development setup.
- `docs/ROADMAP.md` built from this file.
- `docs/DECISIONS.md`.
- `docs/PLATFORMS.md` built from `AGENTS.md`, marked "last verified 2026-09-21".

**Accept:** Every Phase 1 table, endpoint and page named in later Phase 1 tasks appears in `ARCHITECTURE.md`.
**Out of scope:** Code.

### T02: Scaffold · status: done
**Build:**
- Monorepo layout from `AGENTS.md`.
- Docker Compose running web, api, worker, postgres and redis.
- FastAPI health endpoint.
- Next.js shell page.
- A Dramatiq worker that runs a no-op job.
- Alembic set up.
- Lint, format and test tooling for both languages.
- A 30–60 s speech MP4 fixture in `tests/fixtures/`.

**Accept:**
- `docker compose up` from a clean checkout serves the web page and API health check.
- The no-op job runs.
- The test suites run.

**Out of scope:** Domain tables and features.

### T03: Upload, YouTube ingestion and storage · status: todo
**Build:**
- Project and SourceVideo tables (`source_kind`: `local_upload` or `youtube_url`), plus MediaAsset. No rights fields.
- `StorageProvider` with a local-disk adapter.
- Upload endpoint with format and size validation, a generated asset ID, and ffprobe metadata.
- `YouTubeSourceProvider` that downloads a given YouTube URL (e.g. via `yt-dlp`) into a MediaAsset via the `youtube_download` job stage.
- Project page with an add-source form: local file upload, or a YouTube URL field.

**Accept:**
- Uploading the fixture stores the original and its metadata.
- Uploads with unsupported formats are rejected.
- Submitting a YouTube URL downloads the video and stores it as a MediaAsset.
- No filesystem paths appear in API responses.

**Out of scope:** Processing beyond storing the original; rights tracking (intentionally removed, see `docs/DECISIONS.md`).

### T04: Job system · status: todo
**Build:**
- Job table with states (queued, processing, completed, failed), progress and error fields.
- A stage-runner pattern where each stage is idempotent and persists its state before the next stage starts.
- Retry endpoint.
- UI status display, using polling.

**Accept:**
- A deliberately failing test stage shows as failed with its error, and a retry succeeds.
- The upload request returns before any stage runs.

**Out of scope:** Real media stages.

### T05: Audio extraction and transcription · status: todo
**Build:**
- An audio-extraction stage producing 16 kHz mono WAV.
- A `Transcriber` interface with a faster-whisper adapter: large-v3 on CUDA, a smaller model on CPU, word timestamps on.
- Transcript, TranscriptWord and TranscriptSegment tables.
- Transcript view with clickable timestamps that seek the player.

**Accept:**
- The fixture's word timestamps are within about 100 ms.
- Re-running a stage creates no duplicates.
- A 60-minute file completes without API timeouts.

**Out of scope:** Diarization, LLM calls.

---

## Phase 2: Candidate generation

### T06: Signal extraction · status: todo
**Build:** Per-source signals stored as time series:
- Loudness and RMS energy.
- Scene changes, via PySceneDetect.
- Pauses and sentence boundaries from the transcript.
- Speech rate.

**Accept:** Signals are stored for the fixture and visible as a simple timeline chart on the project page.
**Out of scope:** Scoring.

### T07: Candidate windows · status: todo
**Build:**
- Window generation per clip preset from `AGENTS.md`.
- Start and end snapped to sentence boundaries, never starting or ending mid-sentence.
- Overlap between windows allowed.

**Accept:**
- Each preset yields windows within its duration bounds.
- A test confirms no window cuts a sentence.

**Out of scope:** LLM calls.

### T08: LLM provider · status: todo
**Build:**
- `LLMProvider` interface, with one hosted adapter and an optional Ollama adapter.
- Prompts versioned in files.
- JSON output validated by Pydantic, with retry on invalid output.
- Token and cost logging per call.

**Accept:**
- Swapping the adapter via an environment variable works.
- Invalid JSON triggers a retry and then a clean failure.
- The cost of each call is recorded.

**Out of scope:** Clip logic.

### T09: Scoring, ranking and features · status: todo
**Build:**
- LLM scoring of windows: hook line, self-containedness, emotional peak, quotable line, score 0–100, and a reason.
- A combined score from heuristic signals plus the LLM score.
- Dedupe of overlapping candidates.
- ClipCandidate storing its full feature vector plus the model and prompt versions.

**Accept:**
- The fixture produces ranked candidates, each with a reason.
- Features are persisted.
- Re-scoring with a new prompt version keeps the old results.

**Out of scope:** UI beyond the API.

### T10: Candidate review UI · status: todo
**Build:**
- Candidate list with thumbnail, start and end times, duration, preset, transcript excerpt, score and reason.
- In-player preview by seeking.
- Start and end adjustment with sentence snapping.
- Accept or reject per candidate.

**Accept:** Adjusting a candidate's times persists them, and the change shows in the preview.
**Out of scope:** Rendering.

---

## Phase 3: Render

### T11: Basic render · status: todo
**Build:**
- RenderJob and RenderedAsset tables.
- FFmpeg cut to 9:16, 1:1 and 16:9 with a center crop.
- h264_nvenc when available, otherwise x264.
- Signed download URLs.

**Accept:**
- Renders of the fixture play correctly at each aspect ratio.

**Out of scope:** Face tracking, captions. Rights checks are intentionally out of scope for the whole project (see `docs/DECISIONS.md`).

### T12: Face-tracked reframe · status: todo
**Build:**
- Face and active-speaker tracking with MediaPipe.
- A smoothed crop path, with no jitter above a set threshold.
- Fallback to center crop.

**Accept:** On a two-speaker test video, the crop follows the active speaker and the crop path's per-frame movement stays under the threshold.
**Out of scope:** Captions.

### T13: Captions and audio finishing · status: todo
**Build:**
- Word-timestamp-driven ASS captions with word highlighting and style presets.
- Burn-in.
- EBU R128 loudness normalization.

**Accept:**
- Captions stay in sync within 100 ms on the fixture.
- Output loudness is within ±1 LU of target.

**Out of scope:** Reaction track.

---

## Phase 4: Reaction pairing

### T14: Reaction sessions · status: todo
**Build:**
- A "watch sheet" that plays accepted candidates in order, separated by an audible tone and an on-screen clip-ID card, for me to record against.
- ReactionSession upload.
- Transcription of the session.

**Accept:** A session can be recorded against the watch sheet, uploaded, and transcribed.
**Out of scope:** Alignment.

### T15: Reaction alignment · status: todo
**Build:**
- Tone detection by cross-correlation, with an OCR fallback on the clip-ID card.
- Slicing into ReactionSegments linked to candidates.
- A manual override UI for misalignments.

**Accept:**
- A synthetic test session aligns every segment within 100 ms.
- The override UI can fix a deliberately shifted segment.

**Out of scope:** Composition.

### T16: Composed layouts · status: todo
**Build:**
- Stacked layout (reaction on top, about 40%) and picture-in-picture layout.
- Source audio ducked under commentary via sidechain compression.
- Layout chosen per clip.

**Accept:** Renders in both layouts keep the reaction and source in sync, and the source audio ducks audibly under speech.
**Out of scope:** QA gates.

### T17: QA gates and approval states · status: todo
**Build:** Automated checks per render:
- Duration within preset bounds.
- Loudness.
- Black frames and silence.
- Caption coverage.
- A commentary segment of at least 5 s containing speech.
- An optional LLM policy check.

Clip states: draft, qa_failed, pending_review, approved, rejected.

**Accept:**
- Each check has a test with a failing input.
- A clip that fails any check cannot reach `approved`.

**Out of scope:** Publishing.

---

## Phase 5: Review and publish

### T18: Review queue and metadata · status: todo
**Build:**
- A review queue page with approve, reject and send-back-to-recut actions.
- LLM-generated title, description and hashtags per platform, editable before approval.

**Accept:** Approving records the reviewer and a timestamp; edited metadata persists.
**Out of scope:** Uploading.

### T19: Campaign tracking · status: todo
**Build:**
- Campaign entity: marketplace, CPM, budget, remaining budget, rules, and the SourceVideos linked to it.
- A record of submitted post URLs.
- Verified views entered manually.
- Earnings computed from verified views and CPM.

**Accept:** Earnings for each campaign are computed correctly from test data and capped at the campaign budget.
**Out of scope:** Marketplace APIs.

### T20: YouTube publisher and scheduler · status: todo
**Build:**
- PlatformAccount with YouTube OAuth.
- `Publisher` interface with a YouTube adapter using resumable uploads.
- Quota accounting per Google Cloud project.
- A scheduler enforcing pacing from `PLATFORMS.md`.
- Posts stay private until app verification is confirmed.
- Only approved clips can be published.

**Accept:**
- A test clip uploads as private.
- The scheduler refuses to exceed the per-account pacing or the per-project quota.
- An unapproved clip cannot be scheduled.

**Out of scope:** Other platforms.

### T21: TikTok and Instagram publishers · status: todo
**Build:**
- TikTok and Instagram adapters behind feature flags, each enabled only when its audit or app review is approved.
- Or a Postiz adapter, if that is recorded as the decision in `DECISIONS.md`.
- No watermarks or links added to TikTok posts.

**Accept:** Each adapter publishes a test post in the mode its current approval status allows.
**Out of scope:** Analytics.

---

## Phase 6: Measure and learn

### T22: Analytics ingestion · status: todo
**Build:**
- PerformanceMetric table.
- Scheduled pulls at 24 h, 72 h and 7 d after posting: views, average view duration, completion rate, likes, comments, shares, subscribers gained.
- YouTube via the Analytics API first.

**Accept:** Metrics for a published test clip land at each interval and join to its ClipCandidate by ID.
**Out of scope:** Model training.

### T23: Performance dashboard and rubric loop · status: todo
**Build:**
- A dashboard with performance by preset, hook type, niche, layout and source.
- A weekly report of the top and bottom deciles.
- A workflow to draft a revised scoring prompt from that report, stored as a new prompt version.
- A side-by-side comparison of old and new rankings on recent sources.

**Accept:** A new prompt version can be created from the report, compared against the previous one, and activated.
**Out of scope:** Custom ML model training (a later phase, once there are enough published clips).
