"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { Signal, SourceVideoStatus } from "../lib/api";
import { BROWSER_API_BASE_URL } from "../lib/browser-api";
import { SignalsTimeline } from "./SignalsTimeline";

export function SignalsPanel({
  projectId,
  sourceId,
  sourceStatus,
  durationMs,
  signals,
}: {
  projectId: string;
  sourceId: string;
  sourceStatus: SourceVideoStatus;
  durationMs: number | null;
  signals: Signal[];
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExtract() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch(
        `${BROWSER_API_BASE_URL}/projects/${projectId}/sources/${sourceId}/extract-signals`,
        { method: "POST" },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Failed to start signal extraction");
      }
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to start signal extraction",
      );
    } finally {
      setPending(false);
    }
  }

  if (signals.length > 0 && durationMs) {
    return <SignalsTimeline signals={signals} durationMs={durationMs} />;
  }

  if (sourceStatus !== "ready") {
    return null;
  }

  return (
    <div className="panel">
      <p className="eyebrow">Signals</p>
      <button type="button" onClick={handleExtract} disabled={pending}>
        {pending ? "Starting…" : "Extract signals"}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
