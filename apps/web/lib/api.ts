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
  | "transcribe"
  | "signal_extraction"
  | "candidate_scoring";
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

export type SignalType =
  | "loudness_rms"
  | "scene_change"
  | "pause"
  | "speech_rate";

export type SignalPoint = {
  t_ms: number;
  value?: number;
  duration_ms?: number;
};

export type Signal = {
  id: string;
  source_video_id: string;
  signal_type: SignalType;
  unit: string;
  points_json: SignalPoint[];
  created_at: string;
};

export type ReviewStatus = "pending" | "accepted" | "rejected";

export type ClipCandidate = {
  id: string;
  source_video_id: string;
  preset: string;
  start_ms: number;
  end_ms: number;
  heuristic_score: number;
  llm_score: number;
  combined_score: number;
  hook_line: boolean;
  self_contained: boolean;
  emotional_peak: boolean;
  quotable_line: string | null;
  reason: string;
  transcript_excerpt: string;
  feature_vector: Record<string, unknown>;
  model: string;
  prompt_name: string;
  prompt_version: number;
  review_status: ReviewStatus;
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

export function listProjectJobs(projectId: string): Promise<Job[]> {
  return serverJson<Job[]>(`/projects/${projectId}/jobs`);
}

export function listSourceSignals(
  projectId: string,
  sourceId: string,
): Promise<Signal[]> {
  return serverJson<Signal[]>(
    `/projects/${projectId}/sources/${sourceId}/signals`,
  );
}

export function listSourceCandidates(
  projectId: string,
  sourceId: string,
): Promise<ClipCandidate[]> {
  return serverJson<ClipCandidate[]>(
    `/projects/${projectId}/sources/${sourceId}/candidates`,
  );
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
