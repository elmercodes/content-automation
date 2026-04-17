from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from PIL import Image

from alembic import command
from app.config import PROJECT_ROOT, get_settings
from app.db import clear_db_runtime_caches
from app.main import app
from app.web.routes.media import generated_media


def make_image_bytes(*, image_format: str = "PNG", size: tuple[int, int]) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", size, color=(70, 50, 40))
    image.save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.fixture
def isolated_local_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    storage_root = tmp_path / "storage"
    uploads_dir = storage_root / "uploads"
    generated_dir = storage_root / "generated"
    database_path = storage_root / "db" / "app.db"

    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("UPLOADS_DIR", str(uploads_dir))
    monkeypatch.setenv("GENERATED_DIR", str(generated_dir))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("FACEBOOK_PAGE_ID", raising=False)
    monkeypatch.delenv("X_API_KEY", raising=False)

    get_settings.cache_clear()
    clear_db_runtime_caches()
    settings = get_settings()
    for path in settings.local_storage_paths:
        path.mkdir(parents=True, exist_ok=True)

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["database_url"] = settings.database_url
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    command.upgrade(config, "head")

    yield storage_root

    get_settings.cache_clear()
    clear_db_runtime_caches()


@pytest.fixture
def configure_platform_env(monkeypatch: pytest.MonkeyPatch):
    def _configure(
        *,
        instagram: bool = False,
        facebook: bool = False,
        x: bool = False,
    ) -> None:
        if instagram:
            monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "test-instagram-token")
        else:
            monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)

        if facebook:
            monkeypatch.setenv("FACEBOOK_PAGE_ID", "test-facebook-page")
        else:
            monkeypatch.delenv("FACEBOOK_PAGE_ID", raising=False)

        if x:
            monkeypatch.setenv("X_API_KEY", "test-x-key")
        else:
            monkeypatch.delenv("X_API_KEY", raising=False)

        get_settings.cache_clear()
        clear_db_runtime_caches()

    return _configure


async def create_master_post(
    client: AsyncClient,
    *,
    media_sizes: list[tuple[int, int]],
    caption: str = "Launch locally",
    hashtags: str = "#phase7",
) -> int:
    files = [
        (
            "media_files",
            (
                f"image-{index}.png",
                make_image_bytes(size=media_size),
                "image/png",
            ),
        )
        for index, media_size in enumerate(media_sizes)
    ]
    response = await client.post(
        "/compose",
        data={"caption": caption, "hashtags": hashtags},
        files=files,
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    post_id = int(location.split("post_id=")[1])
    return post_id


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
