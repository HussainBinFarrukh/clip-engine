from fastapi import APIRouter
from sqlalchemy.engine import make_url

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    database_url = make_url(settings.database_url)
    return {
        "status": "ok",
        "service": "clip-engine-api",
        "version": "0.1.0",
        "database": database_url.host or "configured",
        "redis": settings.redis_url,
    }
