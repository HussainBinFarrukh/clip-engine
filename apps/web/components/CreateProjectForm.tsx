"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { BROWSER_API_BASE_URL } from "../lib/browser-api";

export function CreateProjectForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const response = await fetch(`${BROWSER_API_BASE_URL}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        throw new Error("Failed to create project");
      }
      setName("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="panel form" onSubmit={handleSubmit}>
      <label htmlFor="project-name">New project name</label>
      <input
        id="project-name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
        minLength={1}
      />
      <button type="submit" disabled={pending || name.trim().length === 0}>
        {pending ? "Creating…" : "Create project"}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
