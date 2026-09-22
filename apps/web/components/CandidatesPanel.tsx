"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type {
  ClipCandidate,
  ReviewStatus,
  SourceVideoStatus,
  Transcript,
} from "../lib/api";
import { BROWSER_API_BASE_URL } from "../lib/browser-api";
import { seekVideoPlayer } from "../lib/video-player";

const SCORABLE_STATUSES: SourceVideoStatus[] = ["ready"];

function formatSeconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}

function reviewStatusClass(status: ReviewStatus): string {
  if (status === "accepted") return "status-uploaded";
  if (status === "rejected") return "status-failed";
  return "status-downloading";
}

function CandidateCard({
  projectId,
  sourceId,
  candidate,
  segments,
  onChanged,
}: {
  projectId: string;
  sourceId: string;
  candidate: ClipCandidate;
  segments: Transcript["segments"];
  onChanged: () => void;
}) {
  const [startMs, setStartMs] = useState(candidate.start_ms);
  const [endMs, setEndMs] = useState(candidate.end_ms);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startOptions = segments.map((s) => s.start_ms);
  const endOptions = segments.map((s) => s.end_ms);
  const timesChanged =
    startMs !== candidate.start_ms || endMs !== candidate.end_ms;

  async function patch(body: Record<string, unknown>) {
    setPending(true);
    setError(null);
    try {
      const response = await fetch(
        `${BROWSER_API_BASE_URL}/projects/${projectId}/sources/${sourceId}/candidates/${candidate.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (!response.ok) {
        const responseBody = await response.json().catch(() => null);
        throw new Error(responseBody?.detail ?? "Update failed");
      }
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setPending(false);
    }
  }

  function handleReview(status: ReviewStatus) {
    patch({ review_status: status });
  }

  function handleSaveTimes() {
    patch({ start_ms: startMs, end_ms: endMs });
  }

  return (
    <li className="candidate-card">
      <img
        className="candidate-thumbnail"
        src={`${BROWSER_API_BASE_URL}/projects/${projectId}/sources/${sourceId}/candidates/${candidate.id}/thumbnail`}
        alt=""
        width={160}
        height={90}
      />

      <div className="candidate-body">
        <div className="candidate-header">
          <span className="status">{candidate.preset}</span>
          <span
            className={`status ${reviewStatusClass(candidate.review_status)}`}
          >
            {candidate.review_status}
          </span>
          <strong>{candidate.combined_score.toFixed(0)}/100</strong>
        </div>

        <p className="candidate-excerpt">{candidate.transcript_excerpt}</p>
        <p className="hint">{candidate.reason}</p>
        {candidate.quotable_line && (
          <p className="hint">&ldquo;{candidate.quotable_line}&rdquo;</p>
        )}

        <div className="candidate-times">
          <label>
            Start
            <select
              value={startMs}
              onChange={(e) => setStartMs(Number(e.target.value))}
            >
              {startOptions.map((ms) => (
                <option key={ms} value={ms}>
                  {formatSeconds(ms)}
                </option>
              ))}
            </select>
          </label>
          <label>
            End
            <select
              value={endMs}
              onChange={(e) => setEndMs(Number(e.target.value))}
            >
              {endOptions.map((ms) => (
                <option key={ms} value={ms}>
                  {formatSeconds(ms)}
                </option>
              ))}
            </select>
          </label>
          <span className="hint">({formatSeconds(endMs - startMs)})</span>
        </div>

        <div className="candidate-actions">
          <button type="button" onClick={() => seekVideoPlayer(startMs)}>
            Preview
          </button>
          {timesChanged && (
            <button type="button" onClick={handleSaveTimes} disabled={pending}>
              Save times
            </button>
          )}
          <button
            type="button"
            onClick={() => handleReview("accepted")}
            disabled={pending || candidate.review_status === "accepted"}
          >
            Accept
          </button>
          <button
            type="button"
            onClick={() => handleReview("rejected")}
            disabled={pending || candidate.review_status === "rejected"}
          >
            Reject
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </li>
  );
}

export function CandidatesPanel({
  projectId,
  sourceId,
  sourceStatus,
  transcript,
  candidates,
}: {
  projectId: string;
  sourceId: string;
  sourceStatus: SourceVideoStatus;
  transcript: Transcript | null;
  candidates: ClipCandidate[];
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleScore() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch(
        `${BROWSER_API_BASE_URL}/projects/${projectId}/sources/${sourceId}/score-candidates`,
        { method: "POST" },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Failed to start scoring");
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start scoring");
    } finally {
      setPending(false);
    }
  }

  if (candidates.length === 0) {
    if (!SCORABLE_STATUSES.includes(sourceStatus)) {
      return null;
    }
    return (
      <div className="panel">
        <p className="eyebrow">Candidates</p>
        <button type="button" onClick={handleScore} disabled={pending}>
          {pending ? "Starting…" : "Score candidates"}
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    );
  }

  return (
    <div className="panel">
      <p className="eyebrow">Candidates</p>
      <button type="button" onClick={handleScore} disabled={pending}>
        {pending ? "Starting…" : "Re-score candidates"}
      </button>
      {error && <p className="error">{error}</p>}

      <ul className="candidate-list">
        {candidates.map((candidate) => (
          <CandidateCard
            key={candidate.id}
            projectId={projectId}
            sourceId={sourceId}
            candidate={candidate}
            segments={transcript?.segments ?? []}
            onChanged={() => router.refresh()}
          />
        ))}
      </ul>
    </div>
  );
}
