"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { Transcript, SourceVideoStatus } from "../lib/api";
import { BROWSER_API_BASE_URL } from "../lib/browser-api";
import { seekVideoPlayer } from "../lib/video-player";

const TRANSCRIBABLE_STATUSES: SourceVideoStatus[] = [
  "uploaded",
  "ready",
  "failed",
];

export function TranscriptPanel({
  projectId,
  sourceId,
  sourceStatus,
  transcript,
}: {
  projectId: string;
  sourceId: string;
  sourceStatus: SourceVideoStatus;
  transcript: Transcript | null;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleTranscribe() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch(
        `${BROWSER_API_BASE_URL}/projects/${projectId}/sources/${sourceId}/transcribe`,
        { method: "POST" },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Failed to start transcription");
      }
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start transcription",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="panel">
      <p className="eyebrow">Transcript</p>

      {!transcript && TRANSCRIBABLE_STATUSES.includes(sourceStatus) && (
        <>
          <button type="button" onClick={handleTranscribe} disabled={pending}>
            {pending ? "Starting…" : "Transcribe"}
          </button>
          {error && <p className="error">{error}</p>}
        </>
      )}

      {!transcript && !TRANSCRIBABLE_STATUSES.includes(sourceStatus) && (
        <p>
          Transcription becomes available once the source finishes processing.
        </p>
      )}

      {transcript && (
        <div className="transcript">
          {transcript.segments.map((segment) => (
            <p key={segment.id} className="transcript-segment">
              {segment.words.map((word) => (
                <button
                  key={word.id}
                  type="button"
                  className="transcript-word"
                  onClick={() => seekVideoPlayer(word.start_ms)}
                  title={`${(word.start_ms / 1000).toFixed(1)}s`}
                >
                  {word.word}{" "}
                </button>
              ))}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
