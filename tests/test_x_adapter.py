from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.platforms import get_platform
from app.platforms.adapters import PostingMediaItem, PostingRequest
from app.platforms.x_adapter import XAdapter


def build_settings(tmp_path: Path) -> Settings:
    storage_root = tmp_path / "storage"
    uploads_dir = storage_root / "uploads"
    generated_dir = storage_root / "generated"
    database_path = storage_root / "db" / "app.db"
    for path in (uploads_dir, generated_dir, database_path.parent):
        path.mkdir(parents=True, exist_ok=True)
    return Settings(
        _env_file=None,
        storage_root=storage_root,
        uploads_dir=uploads_dir,
        generated_dir=generated_dir,
        database_url=f"sqlite:///{database_path}",
        x_api_key="key",
        x_api_secret="secret",
        x_access_token="token",
        x_access_token_secret="token-secret",
    )


def build_request(
    settings: Settings,
    *,
    media_count: int,
) -> PostingRequest:
    media_items: list[PostingMediaItem] = []
    for display_order in range(media_count):
        relative_path = (
            Path("uploads") / "posts" / "4" / f"{display_order:03d}-upload.png"
        )
        absolute_path = settings.storage_root_path / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(b"fake-image-bytes")
        media_items.append(
            PostingMediaItem(
                display_order=display_order,
                original_filename=f"upload-{display_order}.png",
                media_type="image",
                width=1200,
                height=1200,
                file_path=relative_path.as_posix(),
                absolute_path=absolute_path,
            )
        )

    return PostingRequest(
        post_id=4,
        platform_definition=get_platform("x"),
        caption="Launch locally",
        hashtags="#phase9",
        posting_text="Launch locally\n\n#phase9",
        media_items=tuple(media_items),
    )


@pytest.mark.parametrize("media_count", [1, 4])
def test_x_adapter_posts_image_batches_and_normalizes_success(
    tmp_path: Path,
    media_count: int,
) -> None:
    settings = build_settings(tmp_path)
    request = build_request(settings, media_count=media_count)
    uploaded_media_ids: list[str] = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        if str(http_request.url) == XAdapter.MEDIA_UPLOAD_URL:
            media_id = f"media-{len(uploaded_media_ids) + 1}"
            uploaded_media_ids.append(media_id)
            assert http_request.headers["Authorization"].startswith("OAuth ")
            return httpx.Response(200, json={"media_id_string": media_id})
        if str(http_request.url) == XAdapter.STATUS_UPDATE_URL:
            assert http_request.headers["Authorization"].startswith("OAuth ")
            body_text = http_request.content.decode("utf-8")
            assert "status=Launch+locally%0A%0A%23phase9" in body_text
            assert f"media_ids={'%2C'.join(uploaded_media_ids)}" in body_text
            return httpx.Response(
                200,
                json={
                    "id_str": "tweet-123",
                    "extended_entities": {
                        "media": [
                            {"id_str": media_id} for media_id in uploaded_media_ids
                        ]
                    },
                },
            )
        raise AssertionError(
            f"Unexpected request: {http_request.method} {http_request.url}"
        )

    transport = httpx.MockTransport(handler)
    adapter = XAdapter(
        client_factory=lambda: httpx.Client(transport=transport, timeout=30.0)
    )

    result = adapter.submit(
        request,
        settings,
        attempted_at=datetime(2026, 4, 17, 18, 0, tzinfo=UTC),
    )

    assert result.status == "posted"
    assert result.external_post_id == "tweet-123"
    assert result.posted_at == datetime(2026, 4, 17, 18, 0, tzinfo=UTC)
    assert result.response_summary is not None
    assert len(uploaded_media_ids) == media_count


def test_x_adapter_returns_not_configured_when_local_credentials_are_incomplete(
    tmp_path: Path,
) -> None:
    settings = build_settings(tmp_path)
    incomplete_settings = Settings(
        _env_file=None,
        storage_root=settings.storage_root,
        uploads_dir=settings.uploads_dir,
        generated_dir=settings.generated_dir,
        database_url=settings.database_url,
        x_api_key="key",
    )
    request = build_request(settings, media_count=1)
    adapter = XAdapter()

    result = adapter.validate(
        request,
        incomplete_settings,
        attempted_at=datetime(2026, 4, 17, 18, 5, tzinfo=UTC),
    )

    assert result is not None
    assert result.status == "not_configured"
    assert "x_api_secret" in (result.error_message or "")


def test_x_adapter_normalizes_http_failures_to_submission_failed(
    tmp_path: Path,
) -> None:
    settings = build_settings(tmp_path)
    request = build_request(settings, media_count=1)

    def handler(http_request: httpx.Request) -> httpx.Response:
        if str(http_request.url) == XAdapter.MEDIA_UPLOAD_URL:
            return httpx.Response(200, json={"media_id_string": "media-1"})
        if str(http_request.url) == XAdapter.STATUS_UPDATE_URL:
            return httpx.Response(500, text="server error")
        raise AssertionError(
            f"Unexpected request: {http_request.method} {http_request.url}"
        )

    transport = httpx.MockTransport(handler)
    adapter = XAdapter(
        client_factory=lambda: httpx.Client(transport=transport, timeout=30.0)
    )

    result = adapter.submit(
        request,
        settings,
        attempted_at=datetime(2026, 4, 17, 18, 10, tzinfo=UTC),
    )

    assert result.status == "submission_failed"
    assert result.error_message == "X returned HTTP 500."
    assert result.response_summary == "server error"
