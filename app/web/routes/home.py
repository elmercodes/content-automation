from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.accounts_service import list_provider_runtime_states
from app.db import get_session_factory
from app.web.templates import render_page

router = APIRouter()


@router.get("/", name="home", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    session_factory = get_session_factory()
    with session_factory() as db:
        provider_states = list_provider_runtime_states(db)
    return render_page(
        request,
        "pages/home.html",
        page_title="Home",
        active_page="home",
        provider_states=provider_states,
    )
