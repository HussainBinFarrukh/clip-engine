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

export type JobStage =
  | "test_stage"
  | "upload_metadata"
  | "youtube_download"
  | "audio_extract"
  | "transcribe";
export type JobState = "queued" | "processing" | "completed" | "failed";

export type Job = {
  id: string;
  source_video_id: string | null;
  stage: JobStage;
  state: JobState;
  progress: number;
  attempts: number;
  error_code: string | null;
  error_message: string | null;
  output_json: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type TranscriptWord = {
  id: string;
  word: string;
  start_ms: number;
  end_ms: number;
  confidence: number | null;
  word_index: number;
};

export type TranscriptSegment = {
  id: string;
  start_ms: number;
  end_ms: number;
  text: string;
  speaker_label: string | null;
  confidence: number | null;
  words: TranscriptWord[];
};

export type Transcript = {
  id: string;
  source_video_id: string;
  transcriber_name: string;
  transcriber_model: string;
  language: string | null;
  duration_ms: number;
  created_at: string;
  segments: TranscriptSegment[];
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

export function listProjectJobs(projectId: string): Promise<Job[]> {
  return serverJson<Job[]>(`/projects/${projectId}/jobs`);
}

export async function getTranscript(
  sourceId: string,
): Promise<Transcript | null> {
  const response = await fetch(
    `${serverApiBaseUrl()}/sources/${sourceId}/transcript`,
    {
      cache: "no-store",
    },
  );
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(
      `Request to fetch transcript failed with ${response.status}`,
    );
  }
  return response.json() as Promise<Transcript>;
}
