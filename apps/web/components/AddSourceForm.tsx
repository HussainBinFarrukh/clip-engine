"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { BROWSER_API_BASE_URL } from "../lib/browser-api";

type Mode = "upload" | "youtube";

export function AddSourceForm({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("upload");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);

    try {
      if (mode === "youtube") {
        const response = await fetch(
          `${BROWSER_API_BASE_URL}/projects/${projectId}/sources`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: title.trim() || url,
              source_kind: "youtube_url",
              source_reference: url,
            }),
          },
        );
        if (!response.ok) {
          throw new Error(
            await extractError(response, "Failed to add YouTube source"),
          );
        }
        setUrl("");
      } else {
        if (!file) {
          throw new Error("Choose a file to upload");
        }

        const createResponse = await fetch(
          `${BROWSER_API_BASE_URL}/projects/${projectId}/sources`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: title.trim() || file.name,
              source_kind: "local_upload",
            }),
          },
        );
        if (!createResponse.ok) {
          throw new Error(
            await extractError(createResponse, "Failed to create source"),
          );
        }
        const created = (await createResponse.json()) as { id: string };

        const formData = new FormData();
        formData.append("file", file);
        const uploadResponse = await fetch(
          `${BROWSER_API_BASE_URL}/projects/${projectId}/sources/${created.id}/upload`,
          { method: "POST", body: formData },
        );
        if (!uploadResponse.ok) {
          throw new Error(await extractError(uploadResponse, "Upload failed"));
        }
        setFile(null);
      }

      setTitle("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="panel form" onSubmit={handleSubmit}>
      <div className="tabs">
        <button
          type="button"
          className={mode === "upload" ? "active" : ""}
          onClick={() => setMode("upload")}
        >
          Upload file
        </button>
        <button
          type="button"
          className={mode === "youtube" ? "active" : ""}
          onClick={() => setMode("youtube")}
        >
          YouTube URL
        </button>
      </div>

      <label htmlFor="source-title">Title</label>
      <input
        id="source-title"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder="Optional — defaults to file name or URL"
      />

      {mode === "upload" ? (
        <>
          <label htmlFor="source-file">Video file (MP4)</label>
          <input
            id="source-file"
            type="file"
            accept="video/mp4"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </>
      ) : (
        <>
          <label htmlFor="source-url">YouTube URL</label>
          <input
            id="source-url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
          />
          <p className="hint">
            Downloading a YouTube video is done at your own risk and runs
            against YouTube&apos;s Terms of Service. You are responsible for
            having the rights to whatever you provide.
          </p>
        </>
      )}

      <button type="submit" disabled={pending}>
        {pending ? "Adding…" : "Add source"}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}

async function extractError(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
    if (body?.detail) {
      return JSON.stringify(body.detail);
    }
  } catch {
    // ignore parse errors and fall through
  }
  return fallback;
}
