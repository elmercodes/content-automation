from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.compose_service import (
    build_compose_page_context,
    create_master_post,
    load_master_post_summary,
)
from app.db import get_session_factory
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
        **build_compose_page_context(),
    )


@router.get("/platforms", name="platforms", response_class=HTMLResponse)
async def platforms(request: Request, post_id: int | None = None) -> HTMLResponse:
    post_summary = None
    if post_id is not None:
        session_factory = get_session_factory()
        with session_factory() as db:
            post_summary = load_master_post_summary(db, post_id=post_id)
        if post_summary is None:
            raise HTTPException(status_code=404, detail="Master post not found.")

    return render_page(
        request,
        "pages/platforms.html",
        page_title="Platforms",
        active_page="compose",
        workflow_step="platforms",
        post_summary=post_summary,
    )


@router.post("/compose", response_class=HTMLResponse)
async def submit_compose(request: Request) -> Response:
    form_data = await request.form()
    media_files = [
        media_file
        for media_file in form_data.getlist("media_files")
        if hasattr(media_file, "filename")
    ]
    session_factory = get_session_factory()
    with session_factory() as db:
        result = create_master_post(
            db,
            caption=str(form_data.get("caption") or ""),
            hashtags=str(form_data.get("hashtags") or ""),
            media_files=media_files,
        )
    if result.succeeded:
        redirect_target = request.url_for("platforms").include_query_params(
            post_id=result.post_id
        )
        return RedirectResponse(
            url=str(redirect_target),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return render_page(
        request,
        "pages/compose.html",
        page_title="Compose",
        active_page="compose",
        workflow_step="compose",
        status_code=status.HTTP_400_BAD_REQUEST,
        **build_compose_page_context(
            form=result.form,
            field_errors=result.field_errors,
            non_field_errors=result.non_field_errors,
        ),
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
