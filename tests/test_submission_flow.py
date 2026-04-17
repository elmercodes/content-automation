from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import select

from alembic import command
from app import posting_service
from app.config import PROJECT_ROOT, get_settings
from app.db import (
    MediaItem,
    PostPlatformLog,
    clear_db_runtime_caches,
    get_session_factory,
)
from app.main import app
from app.platforms.adapters import PostingResult, UnsupportedPlatformAdapter


def make_image_bytes(*, image_format: str = "PNG", size: tuple[int, int]) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", size, color=(70, 50, 40))
    image.save(buffer, format=image_format)
    return buffer.getvalue()


class SuccessfulAdapter:
    def validate(self, request, settings, *, attempted_at):  # noqa: ANN001, ANN201
        del request, settings, attempted_at
        return None

    def submit(self, request, settings, *, attempted_at):  # noqa: ANN001, ANN201
        del settings
        return PostingResult(
            platform_slug=request.platform_slug,
            status="posted",
            attempted_at=attempted_at,
            posted_at=attempted_at,
            external_post_id="tweet-123",
            response_summary='{"media_ids":["media-1"],"tweet_id":"tweet-123"}',
        )


class FailingAdapter:
    def validate(self, request, settings, *, attempted_at):  # noqa: ANN001, ANN201
        del request, settings, attempted_at
        return None

    def submit(self, request, settings, *, attempted_at):  # noqa: ANN001, ANN201
        del settings
        return PostingResult(
            platform_slug=request.platform_slug,
            status="submission_failed",
            attempted_at=attempted_at,
            error_message=f"{request.platform_display_name} returned a provider error.",
        )


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
    monkeypatch.delenv("X_API_SECRET", raising=False)
    monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("X_ACCESS_TOKEN_SECRET", raising=False)

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

        monkeypatch.delenv("X_API_SECRET", raising=False)
        monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("X_ACCESS_TOKEN_SECRET", raising=False)

        get_settings.cache_clear()
        clear_db_runtime_caches()

    return _configure


async def create_master_post(
    client: AsyncClient,
    *,
    media_sizes: list[tuple[int, int]],
    caption: str = "Launch locally",
    hashtags: str = "#phase9",
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
    return int(response.headers["location"].split("post_id=")[1])


def resolve_test_adapter(platform_slug: str):
    if platform_slug == "x":
        return SuccessfulAdapter()
    return UnsupportedPlatformAdapter(platform_slug)


@pytest.mark.anyio
async def test_review_final_shows_posting_readiness_by_platform(
    isolated_local_runtime: Path,
    configure_platform_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_platform_env(instagram=True, x=True)
    monkeypatch.setattr(
        posting_service,
        "resolve_platform_adapter",
        resolve_test_adapter,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])
        response = await client.get(
            f"/review/final?post_id={post_id}&platform_slug=instagram&platform_slug=x"
        )

    assert response.status_code == 200
    assert "Posting readiness:" in response.text
    assert "Ready" in response.text
    assert "Direct posting is deferred because the current local-only workflow" in (
        response.text
    )


@pytest.mark.anyio
async def test_submit_review_final_records_one_result_per_platform_and_redirects(
    isolated_local_runtime: Path,
    configure_platform_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_platform_env(instagram=True, x=True)
    monkeypatch.setattr(
        posting_service,
        "resolve_platform_adapter",
        resolve_test_adapter,
    )
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36), (36, 48)])
        response = await client.post(
            "/review/final",
            data={
                "post_id": str(post_id),
                "platform_index": "1",
                "platform_slug": ["instagram", "x"],
            },
            follow_redirects=False,
        )
        results_response = await client.get(response.headers["location"])

    assert response.status_code == 303
    assert f"/results?post_id={post_id}" in response.headers["location"]
    assert results_response.status_code == 200
    assert "Submission results" in results_response.text
    assert "Instagram" in results_response.text
    assert "Unsupported" in results_response.text
    assert "X" in results_response.text
    assert "Posted" in results_response.text
    assert "tweet-123" in results_response.text

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        logs = session.scalars(
            select(PostPlatformLog).order_by(PostPlatformLog.platform_slug)
        ).all()

    assert [log.platform_slug for log in logs] == ["instagram", "x"]
    assert [log.status for log in logs] == ["unsupported", "posted"]
    assert logs[0].error_message is not None
    assert logs[0].posted_at is None
    assert logs[1].external_post_id == "tweet-123"
    assert logs[1].posted_at == logs[1].created_at


@pytest.mark.anyio
async def test_submit_review_final_blocks_duplicate_successful_reposts(
    isolated_local_runtime: Path,
    configure_platform_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_platform_env(x=True)
    monkeypatch.setattr(
        posting_service,
        "resolve_platform_adapter",
        resolve_test_adapter,
    )
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])
        first_response = await client.post(
            "/review/final",
            data={"post_id": str(post_id), "platform_index": "0", "platform_slug": "x"},
            follow_redirects=False,
        )
        second_response = await client.post(
            "/review/final",
            data={"post_id": str(post_id), "platform_index": "0", "platform_slug": "x"},
            follow_redirects=False,
        )

    assert first_response.status_code == 303
    assert second_response.status_code == 400
    assert "Successful post platform logs already exist for: x." in second_response.text

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        logs = session.scalars(select(PostPlatformLog)).all()

    assert len(logs) == 1
    assert logs[0].status == "posted"


@pytest.mark.anyio
async def test_submit_review_final_records_validation_failure_when_media_is_missing(
    isolated_local_runtime: Path,
    configure_platform_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_platform_env(x=True)
    monkeypatch.setattr(
        posting_service,
        "resolve_platform_adapter",
        resolve_test_adapter,
    )
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        media_item = session.scalar(
            select(MediaItem).where(MediaItem.post_id == post_id)
        )
        assert media_item is not None
        missing_path = settings.storage_root_path / media_item.file_path
        missing_path.unlink()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/review/final",
            data={"post_id": str(post_id), "platform_index": "0", "platform_slug": "x"},
            follow_redirects=False,
        )
        results_response = await client.get(response.headers["location"])

    assert response.status_code == 303
    assert results_response.status_code == 200
    assert "Validation Failed" in results_response.text
    assert "Local media files are missing" in results_response.text

    with session_factory() as session:
        log = session.scalar(
            select(PostPlatformLog).where(PostPlatformLog.post_id == post_id)
        )

    assert log is not None
    assert log.status == "validation_failed"
    assert log.posted_at is None


@pytest.mark.anyio
async def test_submit_review_final_isolates_submission_failures_per_platform(
    isolated_local_runtime: Path,
    configure_platform_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_platform_env(facebook=True, x=True)

    def resolve_adapter(platform_slug: str):
        if platform_slug == "x":
            return FailingAdapter()
        return UnsupportedPlatformAdapter(platform_slug)

    monkeypatch.setattr(posting_service, "resolve_platform_adapter", resolve_adapter)
    settings = get_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        post_id = await create_master_post(client, media_sizes=[(48, 36)])
        response = await client.post(
            "/review/final",
            data={
                "post_id": str(post_id),
                "platform_index": "0",
                "platform_slug": ["facebook", "x"],
            },
            follow_redirects=False,
        )
        results_response = await client.get(response.headers["location"])

    assert response.status_code == 303
    assert "Submission Failed" in results_response.text
    assert "Unsupported" in results_response.text

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        logs = session.scalars(
            select(PostPlatformLog).order_by(PostPlatformLog.platform_slug)
        ).all()

    assert [log.platform_slug for log in logs] == ["facebook", "x"]
    assert [log.status for log in logs] == ["unsupported", "submission_failed"]
