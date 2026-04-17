from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.compose_service import (
    build_compose_page_context,
    create_master_post,
)
from app.db import get_session_factory
from app.platform_selection_service import (
    build_platform_review_state,
    build_platform_selection_page_context,
    collect_selection_errors,
    load_platform_selection_state,
    validate_platform_selection,
)
from app.preview_service import (
    build_platform_review_page_state,
    build_posting_text_metrics,
)
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
    if post_id is None:
        return render_page(
            request,
            "pages/platforms.html",
            page_title="Platforms",
            active_page="compose",
            workflow_step="platforms",
            **build_platform_selection_page_context(),
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        selection_state = load_platform_selection_state(db, post_id=post_id)
    if selection_state is None:
        raise HTTPException(status_code=404, detail="Master post not found.")

    return render_page(
        request,
        "pages/platforms.html",
        page_title="Platforms",
        active_page="compose",
        workflow_step="platforms",
        **build_platform_selection_page_context(state=selection_state),
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


@router.post("/platforms", response_class=HTMLResponse)
async def submit_platform_selection(request: Request) -> Response:
    form_data = await request.form()
    post_id = _parse_post_id(form_data.get("post_id"))
    selected_platform_slugs = [
        str(platform_slug) for platform_slug in form_data.getlist("platform_slug")
    ]

    if post_id is None:
        return render_page(
            request,
            "pages/platforms.html",
            page_title="Platforms",
            active_page="compose",
            workflow_step="platforms",
            status_code=status.HTTP_400_BAD_REQUEST,
            **build_platform_selection_page_context(
                non_field_errors=[
                    "Save a master post before choosing configured platforms."
                ]
            ),
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        selection_state = load_platform_selection_state(
            db,
            post_id=post_id,
            selected_platform_slugs=selected_platform_slugs,
        )
    if selection_state is None:
        raise HTTPException(status_code=404, detail="Master post not found.")

    result = validate_platform_selection(
        selection_state,
        selected_platform_slugs=selected_platform_slugs,
    )
    if result.succeeded:
        redirect_target = _build_platform_review_redirect_url(
            request,
            post_id=selection_state.post_summary.id,
            selected_platform_slugs=result.selected_platform_slugs,
        )
        return RedirectResponse(
            url=redirect_target,
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return render_page(
        request,
        "pages/platforms.html",
        page_title="Platforms",
        active_page="compose",
        workflow_step="platforms",
        status_code=status.HTTP_400_BAD_REQUEST,
        **build_platform_selection_page_context(
            state=selection_state,
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
async def review_platforms(
    request: Request,
    post_id: int | None = None,
    platform_index: int = 0,
) -> HTMLResponse:
    selected_platform_slugs = request.query_params.getlist("platform_slug")
    if post_id is None and not selected_platform_slugs:
        return render_page(
            request,
            "pages/review_platforms.html",
            page_title="Platform Review",
            active_page="compose",
            workflow_step="review_platforms",
        )

    if post_id is None:
        return render_page(
            request,
            "pages/review_platforms.html",
            page_title="Platform Review",
            active_page="compose",
            workflow_step="review_platforms",
            status_code=status.HTTP_400_BAD_REQUEST,
            review_errors=[
                "Return to platform selection and choose at least one eligible "
                "configured platform."
            ],
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        selection_state = load_platform_selection_state(
            db,
            post_id=post_id,
            selected_platform_slugs=selected_platform_slugs,
        )
    if selection_state is None:
        raise HTTPException(status_code=404, detail="Master post not found.")

    platform_selection_url = str(
        request.url_for("platforms").include_query_params(post_id=post_id)
    )
    result = validate_platform_selection(
        selection_state,
        selected_platform_slugs=selected_platform_slugs,
    )
    if not result.succeeded:
        return render_page(
            request,
            "pages/review_platforms.html",
            page_title="Platform Review",
            active_page="compose",
            workflow_step="review_platforms",
            status_code=status.HTTP_400_BAD_REQUEST,
            review_errors=collect_selection_errors(result),
            platform_selection_url=platform_selection_url,
        )

    review_state = build_platform_review_state(
        selection_state,
        selected_platform_slugs=result.selected_platform_slugs,
    )
    review_page = build_platform_review_page_state(
        review_state,
        platform_index=platform_index,
    )
    current_preview = review_page.current_preview
    current_preview_items = tuple(
        {
            "item_number": preview_item.item_number,
            "media_item": preview_item.media_item,
            "preview_image_url": (
                str(
                    request.url_for(
                        "generated_media",
                        preview_path=preview_item.preview_image.relative_path,
                    )
                )
                if preview_item.preview_image is not None
                else None
            ),
            "error_message": preview_item.error_message,
        }
        for preview_item in current_preview.preview_items
    )

    platform_navigation = tuple(
        {
            "platform": platform,
            "index": index,
            "current": index == review_page.current_platform_index,
            "url": _build_platform_review_url(
                request,
                post_id=review_page.post_id,
                selected_platform_slugs=result.selected_platform_slugs,
                platform_index=index,
            ),
        }
        for index, platform in enumerate(review_page.selected_platforms)
    )

    previous_platform_url = None
    if review_page.current_platform_index > 0:
        previous_platform_url = _build_platform_review_url(
            request,
            post_id=review_page.post_id,
            selected_platform_slugs=result.selected_platform_slugs,
            platform_index=review_page.current_platform_index - 1,
        )

    next_platform_url = None
    review_final_url = None
    if review_page.current_platform_index < review_page.total_platforms - 1:
        next_platform_url = _build_platform_review_url(
            request,
            post_id=review_page.post_id,
            selected_platform_slugs=result.selected_platform_slugs,
            platform_index=review_page.current_platform_index + 1,
        )
    else:
        review_final_url = _build_review_final_url(
            request,
            post_id=review_page.post_id,
            selected_platform_slugs=result.selected_platform_slugs,
            platform_index=review_page.current_platform_index,
        )

    return render_page(
        request,
        "pages/review_platforms.html",
        page_title="Platform Review",
        active_page="compose",
        workflow_step="review_platforms",
        review_state=review_state,
        review_post_summary=review_state.post_summary,
        selected_platforms=review_state.selected_platforms,
        review_page=review_page,
        current_preview=current_preview,
        current_preview_items=current_preview_items,
        platform_navigation=platform_navigation,
        previous_platform_url=previous_platform_url,
        next_platform_url=next_platform_url,
        review_final_url=review_final_url,
        platform_selection_url=platform_selection_url,
        review_errors=[],
    )


@router.get("/review/final", name="review_final", response_class=HTMLResponse)
async def review_final(
    request: Request,
    post_id: int | None = None,
    platform_index: int = 0,
) -> HTMLResponse:
    selected_platform_slugs = request.query_params.getlist("platform_slug")
    if post_id is None and not selected_platform_slugs:
        return render_page(
            request,
            "pages/review_final.html",
            page_title="Final Review",
            active_page="compose",
            workflow_step="review_final",
        )

    if post_id is None:
        return render_page(
            request,
            "pages/review_final.html",
            page_title="Final Review",
            active_page="compose",
            workflow_step="review_final",
            status_code=status.HTTP_400_BAD_REQUEST,
            final_review_errors=[
                "Return to platform review after selecting at least one "
                "configured platform."
            ],
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        selection_state = load_platform_selection_state(
            db,
            post_id=post_id,
            selected_platform_slugs=selected_platform_slugs,
        )
    if selection_state is None:
        raise HTTPException(status_code=404, detail="Master post not found.")

    platform_selection_url = str(
        request.url_for("platforms").include_query_params(post_id=post_id)
    )
    result = validate_platform_selection(
        selection_state,
        selected_platform_slugs=selected_platform_slugs,
    )
    if not result.succeeded:
        return render_page(
            request,
            "pages/review_final.html",
            page_title="Final Review",
            active_page="compose",
            workflow_step="review_final",
            status_code=status.HTTP_400_BAD_REQUEST,
            final_review_errors=collect_selection_errors(result),
            platform_selection_url=platform_selection_url,
        )

    review_state = build_platform_review_state(
        selection_state,
        selected_platform_slugs=result.selected_platform_slugs,
    )
    review_page = build_platform_review_page_state(
        review_state,
        platform_index=platform_index,
    )
    review_platform_url = _build_platform_review_url(
        request,
        post_id=post_id,
        selected_platform_slugs=result.selected_platform_slugs,
        platform_index=review_page.current_platform_index,
    )
    selected_platform_summaries = tuple(
        {
            "platform": platform,
            "text_metrics": build_posting_text_metrics(
                caption=review_state.post_summary.caption,
                hashtags=review_state.post_summary.hashtags,
                limit=platform.caption_limit,
            ),
        }
        for platform in review_state.selected_platforms
    )

    return render_page(
        request,
        "pages/review_final.html",
        page_title="Final Review",
        active_page="compose",
        workflow_step="review_final",
        review_post_summary=review_state.post_summary,
        selected_platforms=review_state.selected_platforms,
        selected_platform_summaries=selected_platform_summaries,
        review_platform_url=review_platform_url,
        platform_selection_url=platform_selection_url,
        final_review_errors=[],
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


def _build_platform_review_redirect_url(
    request: Request,
    *,
    post_id: int,
    selected_platform_slugs: tuple[str, ...],
) -> str:
    query_items = _build_workflow_query_items(
        post_id=post_id,
        selected_platform_slugs=selected_platform_slugs,
    )
    return f"{request.url_for('review_platforms')}?{urlencode(query_items, doseq=True)}"


def _build_platform_review_url(
    request: Request,
    *,
    post_id: int,
    selected_platform_slugs: tuple[str, ...],
    platform_index: int,
) -> str:
    query_items = _build_workflow_query_items(
        post_id=post_id,
        selected_platform_slugs=selected_platform_slugs,
        platform_index=platform_index,
    )
    return f"{request.url_for('review_platforms')}?{urlencode(query_items, doseq=True)}"


def _build_review_final_url(
    request: Request,
    *,
    post_id: int,
    selected_platform_slugs: tuple[str, ...],
    platform_index: int,
) -> str:
    query_items = _build_workflow_query_items(
        post_id=post_id,
        selected_platform_slugs=selected_platform_slugs,
        platform_index=platform_index,
    )
    return f"{request.url_for('review_final')}?{urlencode(query_items, doseq=True)}"


def _build_workflow_query_items(
    *,
    post_id: int,
    selected_platform_slugs: tuple[str, ...],
    platform_index: int | None = None,
) -> list[tuple[str, str]]:
    query_items: list[tuple[str, str]] = [("post_id", str(post_id))]
    query_items.extend(
        ("platform_slug", platform_slug) for platform_slug in selected_platform_slugs
    )
    if platform_index is not None:
        query_items.append(("platform_index", str(platform_index)))
    return query_items


def _parse_post_id(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
