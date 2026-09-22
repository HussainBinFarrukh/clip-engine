from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(
    title="Clip Engine API",
    version="0.1.0",
    summary="Phase 1 scaffold for authorized video ingestion and transcription.",
)

app.include_router(health_router)
