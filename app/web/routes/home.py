from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.web.templates import render_page

router = APIRouter()


@router.get("/", name="home", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "pages/home.html",
        page_title="Home",
        active_page="home",
    )
