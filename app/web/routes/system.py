from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.platforms import get_configured_platforms

router = APIRouter()


@router.get("/health", name="health")
async def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.app_env,
        "database_url": settings.database_url,
        "configured_platforms": [
            platform.slug for platform in get_configured_platforms(settings)
        ],
    }
