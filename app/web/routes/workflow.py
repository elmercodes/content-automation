from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.web.templates import render_page

router = APIRouter()


@router.get("/compose", name="compose", response_class=HTMLResponse)
async def compose(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "pages/compose.html",
        page_title="Compose",
        active_page="compose",
        workflow_step="compose",
    )


@router.get("/platforms", name="platforms", response_class=HTMLResponse)
async def platforms(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "pages/platforms.html",
        page_title="Platforms",
        active_page="compose",
        workflow_step="platforms",
    )


@router.get(
    "/review/platforms",
    name="review_platforms",
    response_class=HTMLResponse,
)
async def review_platforms(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "pages/review_platforms.html",
        page_title="Platform Review",
        active_page="compose",
        workflow_step="review_platforms",
    )


@router.get("/review/final", name="review_final", response_class=HTMLResponse)
async def review_final(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "pages/review_final.html",
        page_title="Final Review",
        active_page="compose",
        workflow_step="review_final",
    )


@router.get("/results", name="results", response_class=HTMLResponse)
async def results(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "pages/results.html",
        page_title="Results",
        active_page="compose",
        workflow_step="results",
    )


@router.get("/history", name="history", response_class=HTMLResponse)
async def history(request: Request) -> HTMLResponse:
    return render_page(
        request,
        "pages/history.html",
        page_title="History",
        active_page="history",
    )
