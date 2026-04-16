from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.platforms import (
    get_configured_platform_context,
    get_supported_platform_context,
)

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

WORKFLOW_STEPS = (
    {"key": "compose", "label": "Compose", "route_name": "compose"},
    {"key": "platforms", "label": "Platforms", "route_name": "platforms"},
    {
        "key": "review_platforms",
        "label": "Platform review",
        "route_name": "review_platforms",
    },
    {"key": "review_final", "label": "Final review", "route_name": "review_final"},
    {"key": "results", "label": "Results", "route_name": "results"},
)


def build_template_context(
    request: Request,
    *,
    page_title: str,
    active_page: str,
    workflow_step: str | None = None,
    **context: Any,
) -> dict[str, Any]:
    settings = get_settings()
    base_context = {
        "request": request,
        "settings": settings,
        "page_title": page_title,
        "active_page": active_page,
        "workflow_step": workflow_step,
        "workflow_steps": WORKFLOW_STEPS,
        "supported_platforms": get_supported_platform_context(settings),
        "configured_platforms": get_configured_platform_context(settings),
    }
    base_context.update(context)
    return base_context


def render_page(
    request: Request,
    template_name: str,
    *,
    page_title: str,
    active_page: str,
    workflow_step: str | None = None,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template_name,
        build_template_context(
            request,
            page_title=page_title,
            active_page=active_page,
            workflow_step=workflow_step,
            **context,
        ),
        status_code=status_code,
    )
