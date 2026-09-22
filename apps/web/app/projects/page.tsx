import Link from "next/link";

import { CreateProjectForm } from "../../components/CreateProjectForm";
import { listProjects } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const projects = await listProjects();

  return (
    <main>
      <section className="shell">
        <div>
          <p className="eyebrow">Clip Engine</p>
          <h1>Projects</h1>
        </div>

        <CreateProjectForm />

        <div className="panel">
          {projects.length === 0 ? (
            <p>No projects yet.</p>
          ) : (
            <ul className="list">
              {projects.map((project) => (
                <li key={project.id}>
                  <Link href={`/projects/${project.id}`}>{project.name}</Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}
