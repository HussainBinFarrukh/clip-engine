import Link from "next/link";

import { AddSourceForm } from "../../../components/AddSourceForm";
import { getProject, listSources } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [project, sources] = await Promise.all([
    getProject(id),
    listSources(id),
  ]);

  return (
    <main>
      <section className="shell">
        <div>
          <p className="eyebrow">Project</p>
          <h1>{project.name}</h1>
        </div>

        <AddSourceForm projectId={project.id} />

        <div className="panel">
          {sources.length === 0 ? (
            <p>No sources yet.</p>
          ) : (
            <ul className="list">
              {sources.map((source) => (
                <li key={source.id}>
                  <Link href={`/projects/${project.id}/sources/${source.id}`}>
                    {source.title}
                  </Link>
                  <span className={`status status-${source.status}`}>
                    {source.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}
