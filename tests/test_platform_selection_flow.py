from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.helpers import create_master_post


@pytest.mark.anyio
async def test_platforms_page_without_post_id_guides_user_to_compose(
    isolated_local_runtime: Path,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/platforms")

    assert response.status_code == 200
    assert "Save a master post before choosing platforms" in response.text
    assert "No platforms are configured locally" in response.text


@pytest.mark.anyio
async def test_platforms_page_shows_only_configured_platforms_for_master_post(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True, facebook=True, x=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])
        response = await client.get(f"/platforms?post_id={post_id}")

    assert response.status_code == 200
    assert "Choose configured platforms" in response.text
    assert 'value="instagram"' in response.text
    assert 'value="facebook"' in response.text
    assert 'value="x"' not in response.text


@pytest.mark.anyio
async def test_platforms_page_marks_facebook_ineligible_for_multi_image_post(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True, facebook=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36), (36, 48)])
        response = await client.get(f"/platforms?post_id={post_id}")

    assert response.status_code == 200
    assert 'value="instagram"' in response.text
    assert 'value="facebook"' not in response.text
    assert "Facebook does not support multi-image carousel posts" in response.text


@pytest.mark.anyio
async def test_platforms_page_marks_x_ineligible_when_carousel_exceeds_limit(
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
            media_sizes=[(48, 36), (36, 48), (32, 32), (28, 28), (24, 24)],
        )
        response = await client.get(f"/platforms?post_id={post_id}")

    assert response.status_code == 200
    assert 'value="x"' not in response.text
    assert "X currently supports up to 4 media items in this workflow." in response.text


@pytest.mark.anyio
async def test_submit_platform_selection_requires_one_platform(
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
        response = await client.post(
            "/platforms",
            data={"post_id": str(post_id)},
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert "Select at least one configured platform before continuing." in response.text


@pytest.mark.anyio
async def test_submit_platform_selection_rejects_unconfigured_platforms(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True, x=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])
        response = await client.post(
            "/platforms",
            data={"post_id": str(post_id), "platform_slug": ["instagram", "x"]},
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert "Choose only configured platforms shown on this page." in response.text
    assert 'value="instagram"' in response.text
    assert 'value="x"' not in response.text


@pytest.mark.anyio
async def test_submit_platform_selection_rejects_ineligible_platforms(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True, facebook=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36), (36, 48)])
        response = await client.post(
            "/platforms",
            data={"post_id": str(post_id), "platform_slug": "facebook"},
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert (
        "Remove platforms that are not eligible for this master post yet."
        in response.text
    )


@pytest.mark.anyio
async def test_valid_platform_selection_redirects_to_review_step_in_registry_order(
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
        response = await client.post(
            "/platforms",
            data={"post_id": str(post_id), "platform_slug": ["x", "instagram"]},
            follow_redirects=False,
        )
        review_response = await client.get(response.headers["location"])

    assert response.status_code == 303
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["post_id"] == [str(post_id)]
    assert query["platform_slug"] == ["instagram", "x"]
    assert review_response.status_code == 200
    assert "Preview selected platforms" in review_response.text
    assert "Instagram" in review_response.text
    assert "X" in review_response.text
    assert "Current platform" in review_response.text
    assert "Next platform" in review_response.text


@pytest.mark.anyio
async def test_review_platforms_requires_selected_platforms_when_post_id_present(
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
        response = await client.get(f"/review/platforms?post_id={post_id}")

    assert response.status_code == 400
    assert "Select at least one configured platform before continuing." in response.text
    assert f"/platforms?post_id={post_id}" in response.text


@pytest.mark.anyio
async def test_review_platforms_returns_404_for_unknown_master_post(
    isolated_local_runtime: Path,
    configure_platform_env,
) -> None:
    configure_platform_env(instagram=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/review/platforms?post_id=999&platform_slug=instagram"
        )

    assert response.status_code == 404
