export type Project = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
};

export type SourceKind = "local_upload" | "youtube_url";

export type SourceVideoStatus =
  | "draft"
  | "uploaded"
  | "downloading"
  | "processing"
  | "ready"
  | "failed";

export type SourceVideo = {
  id: string;
  project_id: string;
  title: string;
  source_kind: SourceKind;
  source_reference: string | null;
  duration_ms: number | null;
  width: number | null;
  height: number | null;
  frame_rate: string | null;
  status: SourceVideoStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type MediaAsset = {
  id: string;
  source_video_id: string;
  asset_kind: string;
  mime_type: string;
  byte_size: number;
  checksum_sha256: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

function serverApiBaseUrl(): string {
  return process.env.API_BASE_URL ?? "http://localhost:8000";
}

async function serverJson<T>(path: string): Promise<T> {
  const response = await fetch(`${serverApiBaseUrl()}${path}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function listProjects(): Promise<Project[]> {
  return serverJson<Project[]>("/projects");
}

export function getProject(projectId: string): Promise<Project> {
  return serverJson<Project>(`/projects/${projectId}`);
}

export function listSources(projectId: string): Promise<SourceVideo[]> {
  return serverJson<SourceVideo[]>(`/projects/${projectId}/sources`);
}

export function getSource(
  projectId: string,
  sourceId: string,
): Promise<SourceVideo> {
  return serverJson<SourceVideo>(`/projects/${projectId}/sources/${sourceId}`);
}

export function listSourceAssets(
  projectId: string,
  sourceId: string,
): Promise<MediaAsset[]> {
  return serverJson<MediaAsset[]>(
    `/projects/${projectId}/sources/${sourceId}/assets`,
  );
}
