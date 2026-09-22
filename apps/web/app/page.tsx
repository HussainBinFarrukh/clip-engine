const pipelineSteps = [
  "Ingest",
  "Transcribe",
  "Find moments",
  "Render",
  "Review",
  "Publish",
];

export default function Home() {
  return (
    <main>
      <section className="shell">
        <div>
          <p className="eyebrow">Clip Engine</p>
          <h1>Authorized video clipping pipeline</h1>
        </div>

        <div className="panel">
          <p>
            T02 scaffold is live: Next.js web, FastAPI API, Dramatiq worker,
            PostgreSQL, Redis, Alembic, and test tooling. Feature work starts
            after the scaffold passes.
          </p>
        </div>

        <div className="grid" aria-label="Pipeline stages">
          {pipelineSteps.map((step) => (
            <div className="stat" key={step}>
              <strong>{step}</strong>
              <p>Phase-ready shell</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
