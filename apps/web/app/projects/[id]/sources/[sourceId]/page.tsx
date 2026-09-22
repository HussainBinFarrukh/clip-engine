import { CandidatesPanel } from "../../../../../components/CandidatesPanel";
import { JobsPanel } from "../../../../../components/JobsPanel";
import { SignalsPanel } from "../../../../../components/SignalsPanel";
import { TranscriptPanel } from "../../../../../components/TranscriptPanel";
import {
  getSource,
  getTranscript,
  listSourceAssets,
  listSourceCandidates,
  listSourceSignals,
} from "../../../../../lib/api";
import { BROWSER_API_BASE_URL } from "../../../../../lib/browser-api";
import { VIDEO_PLAYER_ELEMENT_ID } from "../../../../../lib/video-player";

export const dynamic = "force-dynamic";

export default async function SourceDetailPage({
  params,
}: {
  params: Promise<{ id: string; sourceId: string }>;
}) {
  const { id, sourceId } = await params;
  const [source, assets, transcript, signals, candidates] = await Promise.all([
    getSource(id, sourceId),
    listSourceAssets(id, sourceId),
    getTranscript(sourceId),
    listSourceSignals(id, sourceId),
    listSourceCandidates(id, sourceId),
  ]);

  const videoAsset = assets.find(
    (asset) => asset.asset_kind === "original_video",
  );

  return (
    <main>
      <section className="shell">
        <div>
          <p className="eyebrow">Source</p>
          <h1>{source.title}</h1>
        </div>

        <div className="panel">
          <p>Status: {source.status}</p>
          {source.error_message && (
            <p className="error">{source.error_message}</p>
          )}
          <p>Kind: {source.source_kind}</p>
          {source.source_reference && (
            <p>Reference: {source.source_reference}</p>
          )}
          {source.duration_ms !== null && (
            <p>Duration: {(source.duration_ms / 1000).toFixed(1)}s</p>
          )}
          {source.width && source.height && (
            <p>
              Resolution: {source.width}x{source.height}
            </p>
          )}
        </div>

        {videoAsset && (
          <div className="panel">
            <video
              id={VIDEO_PLAYER_ELEMENT_ID}
              controls
              style={{ width: "100%", maxWidth: 640 }}
              src={`${BROWSER_API_BASE_URL}/projects/${id}/sources/${sourceId}/assets/${videoAsset.id}/content`}
            />
          </div>
        )}

        <TranscriptPanel
          projectId={id}
          sourceId={sourceId}
          sourceStatus={source.status}
          transcript={transcript}
        />

        <SignalsPanel
          projectId={id}
          sourceId={sourceId}
          sourceStatus={source.status}
          durationMs={source.duration_ms}
          signals={signals}
        />

        <CandidatesPanel
          projectId={id}
          sourceId={sourceId}
          sourceStatus={source.status}
          transcript={transcript}
          candidates={candidates}
        />

        <JobsPanel projectId={id} sourceId={sourceId} />
      </section>
    </main>
  );
}
