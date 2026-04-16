from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import select

from alembic import command
from app.config import PROJECT_ROOT, get_settings
from app.db import MediaItem, Post, clear_db_runtime_caches, get_session_factory
from app.main import app


def make_image_bytes(*, image_format: str = "PNG", size: tuple[int, int]) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", size, color=(90, 60, 40))
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def list_uploaded_files(upload_root: Path) -> list[Path]:
    return sorted(path for path in upload_root.rglob("*") if path.is_file())


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


@pytest.mark.anyio
async def test_compose_page_renders_real_form(
    isolated_local_runtime: Path,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/compose")

    assert response.status_code == 200
    assert "Create a master post" in response.text
    assert 'enctype="multipart/form-data"' in response.text
    assert 'name="caption"' in response.text
    assert 'name="hashtags"' in response.text
    assert 'name="media_files"' in response.text
    assert "Save master post" in response.text


@pytest.mark.anyio
async def test_compose_post_creates_master_post_and_redirects(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/compose",
            data={
                "caption": "  Launch day  ",
                "hashtags": "  #local #phase5  ",
            },
            files=[
                (
                    "media_files",
                    (
                        "cover.png",
                        make_image_bytes(size=(48, 36)),
                        "image/png",
                    ),
                )
            ],
            follow_redirects=False,
        )

        assert response.status_code == 303
        location = response.headers["location"]

        redirect_response = await client.get(location)

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        posts = session.scalars(select(Post)).all()
        media_items = session.scalars(select(MediaItem).order_by(MediaItem.id)).all()

    assert len(posts) == 1
    assert posts[0].caption == "Launch day"
    assert posts[0].hashtags == "#local #phase5"
    assert len(media_items) == 1
    assert media_items[0].original_filename == "cover.png"
    assert media_items[0].display_order == 0
    assert media_items[0].width == 48
    assert media_items[0].height == 36
    assert media_items[0].media_type == "image"
    assert (settings.storage_root_path / media_items[0].file_path).exists()
    assert "Master post saved locally" in redirect_response.text
    assert "Launch day" in redirect_response.text
    assert "#local #phase5" in redirect_response.text

    query = parse_qs(urlparse(location).query)
    assert query["post_id"] == [str(posts[0].id)]


@pytest.mark.anyio
async def test_compose_post_preserves_upload_order_for_media_items(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/compose",
            data={"caption": "", "hashtags": ""},
            files=[
                (
                    "media_files",
                    (
                        "second.png",
                        make_image_bytes(size=(20, 20)),
                        "image/png",
                    ),
                ),
                (
                    "media_files",
                    (
                        "first.webp",
                        make_image_bytes(image_format="WEBP", size=(12, 18)),
                        "image/webp",
                    ),
                ),
            ],
            follow_redirects=False,
        )

    assert response.status_code == 303

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        post = session.scalar(select(Post).where(Post.caption == ""))
        assert post is not None
        media_items = session.scalars(
            select(MediaItem)
            .where(MediaItem.post_id == post.id)
            .order_by(MediaItem.display_order)
        ).all()

    assert [item.display_order for item in media_items] == [0, 1]
    assert [item.original_filename for item in media_items] == [
        "second.png",
        "first.webp",
    ]
    assert media_items[0].width == 20
    assert media_items[0].height == 20
    assert media_items[1].width == 12
    assert media_items[1].height == 18
    assert Path(media_items[0].file_path).name.startswith("000-")
    assert Path(media_items[1].file_path).name.startswith("001-")


@pytest.mark.anyio
async def test_compose_post_requires_media_files(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/compose",
            data={"caption": "Only text", "hashtags": "#missing"},
            files=[],
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert "Select at least one image" in response.text
    assert "selected again before retrying" in response.text

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        assert session.scalars(select(Post)).all() == []
        assert session.scalars(select(MediaItem)).all() == []

    assert list_uploaded_files(settings.uploads_path) == []


@pytest.mark.anyio
async def test_compose_post_rejects_invalid_uploads_without_partial_state(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/compose",
            data={"caption": "Bad upload", "hashtags": "#invalid"},
            files=[
                (
                    "media_files",
                    (
                        "good.png",
                        make_image_bytes(size=(16, 16)),
                        "image/png",
                    ),
                ),
                (
                    "media_files",
                    (
                        "bad.png",
                        b"not actually an image",
                        "image/png",
                    ),
                ),
            ],
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert "bad.png is not a readable image." in response.text

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        assert session.scalars(select(Post)).all() == []
        assert session.scalars(select(MediaItem)).all() == []

    assert list_uploaded_files(settings.uploads_path) == []


@pytest.mark.anyio
async def test_compose_post_rejects_too_many_files(
    isolated_local_runtime: Path,
) -> None:
    settings = get_settings()
    files = [
        (
            "media_files",
            (
                f"image-{index}.png",
                make_image_bytes(size=(10 + index, 10 + index)),
                "image/png",
            ),
        )
        for index in range(11)
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/compose",
            data={"caption": "Too many", "hashtags": "#bulk"},
            files=files,
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert "Select up to 10 images per master post." in response.text

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        assert session.scalars(select(Post)).all() == []
        assert session.scalars(select(MediaItem)).all() == []

    assert list_uploaded_files(settings.uploads_path) == []


@pytest.mark.anyio
async def test_platforms_page_returns_404_for_unknown_master_post(
    isolated_local_runtime: Path,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/platforms?post_id=999")

    assert response.status_code == 404
