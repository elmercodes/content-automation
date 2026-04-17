from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app
from app.web.routes.media import generated_media
from tests.helpers import create_master_post


@pytest.mark.anyio
async def test_review_platforms_renders_generated_preview_and_navigation(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True, x=True)
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])
        response = await client.get(
            f"/review/platforms?post_id={post_id}&platform_slug=instagram&platform_slug=x"
        )

    assert response.status_code == 200
    assert "Preview selected platforms" in response.text
    assert "Current platform" in response.text
    assert (
        f"/media/generated/previews/v1/posts/{post_id}/instagram/media-000.png"
        in response.text
    )
    assert "Next platform" in response.text
    assert (
        settings.generated_path
        / "previews"
        / "v1"
        / "posts"
        / str(post_id)
        / "instagram"
        / "media-000.png"
    ).exists()


@pytest.mark.anyio
async def test_review_platforms_renders_all_ordered_carousel_preview_items(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True)
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36), (36, 48)])
        response = await client.get(
            f"/review/platforms?post_id={post_id}&platform_slug=instagram"
        )

    assert response.status_code == 200
    assert "Image carousel" in response.text
    assert "Item 1" in response.text
    assert "Item 2" in response.text
    assert (
        f"/media/generated/previews/v1/posts/{post_id}/instagram/media-000.png"
        in response.text
    )
    assert (
        f"/media/generated/previews/v1/posts/{post_id}/instagram/media-001.png"
        in response.text
    )
    assert (
        settings.generated_path
        / "previews"
        / "v1"
        / "posts"
        / str(post_id)
        / "instagram"
        / "media-001.png"
    ).exists()


@pytest.mark.anyio
async def test_review_platforms_shows_over_limit_warning_for_x(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(x=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(
            client,
            media_sizes=[(48, 36)],
            caption="x" * 279,
            hashtags="#phase7",
        )
        response = await client.get(
            f"/review/platforms?post_id={post_id}&platform_slug=x"
        )

    assert response.status_code == 200
    assert "exceeds the X limit of 280" in response.text
    assert "Character count" in response.text
    assert "/ 280" in response.text


@pytest.mark.anyio
async def test_generated_media_route_serves_preview_files_and_rejects_invalid_paths(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])
        await client.get(f"/review/platforms?post_id={post_id}&platform_slug=instagram")

    image_response = await generated_media(
        f"previews/v1/posts/{post_id}/instagram/media-000.png"
    )

    assert image_response.status_code == 200
    assert str(image_response.path).endswith(
        f"/previews/v1/posts/{post_id}/instagram/media-000.png"
    )
    with pytest.raises(HTTPException) as exc_info:
        await generated_media(f"previews/v1/posts/{post_id}/instagram/missing.png")
    assert exc_info.value.status_code == 404
    with pytest.raises(HTTPException) as exc_info:
        await generated_media("../../app/main.py")
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_review_final_preserves_selected_platform_handoff(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True, x=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])
        response = await client.get(
            f"/review/final?post_id={post_id}&platform_slug=instagram&platform_slug=x&platform_index=1"
        )

    assert response.status_code == 200
    assert "Submission checkpoint" in response.text
    assert "Back to previews" in response.text
    assert "Instagram" in response.text
    assert "X" in response.text
    assert "Single image" in response.text
    assert "Submit to selected platforms" in response.text
