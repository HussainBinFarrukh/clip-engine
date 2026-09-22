import { JobsPanel } from "../../../../../components/JobsPanel";
import { getSource, listSourceAssets } from "../../../../../lib/api";
import { BROWSER_API_BASE_URL } from "../../../../../lib/browser-api";

export const dynamic = "force-dynamic";

export default async function SourceDetailPage({
  params,
}: {
  params: Promise<{ id: string; sourceId: string }>;
}) {
  const { id, sourceId } = await params;
  const [source, assets] = await Promise.all([
    getSource(id, sourceId),
    listSourceAssets(id, sourceId),
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
              controls
              style={{ width: "100%", maxWidth: 640 }}
              src={`${BROWSER_API_BASE_URL}/projects/${id}/sources/${sourceId}/assets/${videoAsset.id}/content`}
            />
          </div>
        )}

        <JobsPanel projectId={id} sourceId={sourceId} />
      </section>
    </main>
  );
}
