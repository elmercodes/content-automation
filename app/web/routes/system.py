from __future__ import annotations

from fastapi import APIRouter

from app.accounts_service import list_provider_runtime_states
from app.config import get_settings
from app.db import get_session_factory

router = APIRouter()


@router.get("/health", name="health")
async def health() -> dict[str, object]:
    settings = get_settings()
    session_factory = get_session_factory()
    with session_factory() as db:
        provider_states = list_provider_runtime_states(db, settings=settings)
    return {
        "status": "ok",
        "environment": settings.app_env,
        "database_url": settings.database_url,
        "app_configured_platforms": [
            state.platform.slug for state in provider_states if state.app_configured
        ],
        "connected_platforms": [
            state.platform.slug for state in provider_states if state.connected
        ],
        "ready_to_post_platforms": [
            state.platform.slug for state in provider_states if state.ready_to_post
        ],
    }
