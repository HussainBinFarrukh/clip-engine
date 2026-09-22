from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.projects import router as projects_router
from app.api.sources import router as sources_router
from app.api.sources import transcript_router

app = FastAPI(
    title="Clip Engine API",
    version="0.1.0",
    summary="Phase 1 video ingestion and transcription pipeline.",
)

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(sources_router)
app.include_router(transcript_router)
app.include_router(jobs_router)
