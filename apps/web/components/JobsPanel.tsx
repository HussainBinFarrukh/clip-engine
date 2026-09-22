"use client";

import { useCallback, useEffect, useState } from "react";

import { BROWSER_API_BASE_URL } from "../lib/browser-api";
import type { Job } from "../lib/api";

const POLL_INTERVAL_MS = 3000;

export function JobsPanel({
  projectId,
  sourceId,
}: {
  projectId: string;
  sourceId: string;
}) {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(
        `${BROWSER_API_BASE_URL}/projects/${projectId}/jobs`,
      );
      if (!response.ok) return;
      const allJobs = (await response.json()) as Job[];
      setJobs(allJobs.filter((job) => job.source_video_id === sourceId));
    } catch {
      // Polling failure is non-fatal; the next tick will retry.
    }
  }, [projectId, sourceId]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleRetry(jobId: string) {
    setRetryingId(jobId);
    try {
      await fetch(`${BROWSER_API_BASE_URL}/jobs/${jobId}/retry`, {
        method: "POST",
      });
      await refresh();
    } finally {
      setRetryingId(null);
    }
  }

  if (jobs === null || jobs.length === 0) {
    return null;
  }

  return (
    <div className="panel">
      <p className="eyebrow">Jobs</p>
      <ul className="list">
        {jobs.map((job) => (
          <li key={job.id}>
            <div>
              <strong>{job.stage}</strong>
              <span className={`status status-${jobState(job.state)}`}>
                {job.state}
              </span>
              {job.error_message && (
                <p className="error">{job.error_message}</p>
              )}
            </div>
            {job.state === "failed" && (
              <button
                type="button"
                onClick={() => handleRetry(job.id)}
                disabled={retryingId === job.id}
              >
                {retryingId === job.id ? "Retrying…" : "Retry"}
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function jobState(state: Job["state"]): string {
  // Reuse the source-status color classes (uploaded/failed/downloading share
  // the same visual language as job completed/failed/processing).
  if (state === "completed") return "uploaded";
  if (state === "processing" || state === "queued") return "downloading";
  return state;
}
