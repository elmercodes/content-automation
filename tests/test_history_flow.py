from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.db import (
    MediaItem,
    Post,
    PostPlatformLog,
    get_session_factory,
)
from app.main import app
from app.web.routes.media import uploaded_media
from tests.helpers import create_master_post


def add_logs_for_post(post_id: int, *, x_status: str, instagram_status: str) -> None:
    settings = get_settings()
    session_factory = get_session_factory(settings)
    with session_factory() as session:
        session.add_all(
            [
                PostPlatformLog(
                    post_id=post_id,
                    platform_slug="x",
                    status=x_status,
                    external_post_id="tweet-history" if x_status == "posted" else None,
                    error_message=(
                        "X provider error." if x_status == "submission_failed" else None
                    ),
                ),
                PostPlatformLog(
                    post_id=post_id,
                    platform_slug="instagram",
                    status=instagram_status,
                    error_message=(
                        "Instagram direct posting is deferred."
                        if instagram_status == "unsupported"
                        else None
                    ),
                ),
            ]
        )
        session.commit()


@pytest.mark.anyio
async def test_history_page_shows_empty_state_when_no_posts(
    isolated_local_runtime: Path,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/history")

    assert response.status_code == 200
    assert "No saved posts yet" in response.text


@pytest.mark.anyio
async def test_history_page_lists_posts_newest_first(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        older_post_id = await create_master_post(
            client,
            media_sizes=[(48, 36)],
            caption="Older history entry",
            hashtags="#older",
        )
        newer_post_id = await create_master_post(
            client,
            media_sizes=[(48, 36), (36, 48)],
            caption="Newer history entry",
            hashtags="#newer",
        )

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        older_post = session.scalar(select(Post).where(Post.id == older_post_id))
        newer_post = session.scalar(select(Post).where(Post.id == newer_post_id))
        assert older_post is not None
        assert newer_post is not None
        older_post.created_at = older_post.created_at.replace(day=16)
        older_post.updated_at = older_post.created_at
        newer_post.created_at = newer_post.created_at.replace(day=17)
        newer_post.updated_at = newer_post.created_at
        session.commit()

    add_logs_for_post(newer_post_id, x_status="posted", instagram_status="unsupported")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/history")

    assert response.status_code == 200
    assert "Local content ledger" in response.text
    assert response.text.index("Newer history entry") < response.text.index(
        "Older history entry"
    )
    assert "Image carousel · 2 items" in response.text
    assert "View details" in response.text


@pytest.mark.anyio
async def test_history_detail_page_shows_ordered_media_and_attempt_history(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_id = await create_master_post(
            client,
            media_sizes=[(48, 36), (36, 48)],
            caption="Detail history caption",
            hashtags="#detail",
        )

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        session.add_all(
            [
                PostPlatformLog(
                    post_id=post_id,
                    platform_slug="x",
                    status="submission_failed",
                    error_message="First attempt failed.",
                ),
                PostPlatformLog(
                    post_id=post_id,
                    platform_slug="x",
                    status="posted",
                    external_post_id="tweet-42",
                ),
                PostPlatformLog(
                    post_id=post_id,
                    platform_slug="instagram",
                    status="unsupported",
                    error_message="Deferred provider.",
                ),
            ]
        )
        session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/history/{post_id}")

    assert response.status_code == 200
    assert "Detail history caption" in response.text
    assert "#detail" in response.text
    assert "Item 1" in response.text
    assert "Item 2" in response.text
    assert "Latest platform outcomes" in response.text
    assert "Posting attempt history" in response.text
    assert "tweet-42" in response.text
    assert "Deferred provider." in response.text
    assert "Submission Failed" in response.text


@pytest.mark.anyio
async def test_results_page_links_to_history_views(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_id = await create_master_post(
            client,
            media_sizes=[(48, 36)],
            caption="Results history link caption",
            hashtags="#results",
        )

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        session.add(
            PostPlatformLog(
                post_id=post_id,
                platform_slug="x",
                status="posted",
                external_post_id="tweet-99",
            )
        )
        session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/results?post_id={post_id}&platform_slug=x")

    assert response.status_code == 200
    assert "View history entry" in response.text
    assert f"/history/{post_id}" in response.text
    assert "View all history" in response.text


@pytest.mark.anyio
async def test_uploaded_media_route_serves_uploaded_files_and_rejects_invalid_paths(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_id = await create_master_post(
            client,
            media_sizes=[(48, 36)],
            caption="Media route caption",
            hashtags="#media",
        )

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        media_item = session.scalar(
            select(MediaItem).where(MediaItem.post_id == post_id)
        )
        assert media_item is not None
        upload_path = media_item.file_path.removeprefix("uploads/")

    image_response = await uploaded_media(upload_path)
    assert image_response.status_code == 200
    assert str(image_response.path).endswith(upload_path)
    with pytest.raises(HTTPException) as exc_info:
        await uploaded_media("posts/missing.png")
    assert exc_info.value.status_code == 404
    with pytest.raises(HTTPException) as exc_info:
        await uploaded_media("../../app/main.py")
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_history_detail_page_returns_404_for_missing_post(
    isolated_local_runtime: Path,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/history/9999")

    assert response.status_code == 404
