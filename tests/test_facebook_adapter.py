from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.config import Settings
from app.platforms import get_platform
from app.platforms.adapters import (
    PostingConnectedAccount,
    PostingMediaItem,
    PostingRequest,
)
from app.platforms.facebook_adapter import FacebookAdapter


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
        facebook_client_id="facebook-client-id",
        facebook_client_secret="facebook-client-secret",
    )


def build_request(settings: Settings, *, media_count: int) -> PostingRequest:
    media_items: list[PostingMediaItem] = []
    for display_order in range(media_count):
        relative_path = (
            Path("uploads") / "posts" / "8" / f"{display_order:03d}-upload.png"
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
        post_id=8,
        platform_definition=get_platform("facebook"),
        caption="Launch locally",
        hashtags="#facebook",
        posting_text="Launch locally\n\n#facebook",
        media_items=tuple(media_items),
        connected_account=PostingConnectedAccount(
            provider_slug="facebook",
            provider_account_id="facebook-page-1",
            display_name="Story Mimic",
            username=None,
            access_token="facebook-page-token",
            refresh_token=None,
            token_type="Bearer",
            scopes=("pages_show_list", "pages_manage_posts"),
        ),
    )


def test_facebook_adapter_posts_local_single_image_successfully(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    request = build_request(settings, media_count=1)

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert str(http_request.url) == (
            "https://graph.facebook.com/"
            f"{settings.meta_api_version}/facebook-page-1/photos"
        )
        assert http_request.headers["Authorization"] == "Bearer facebook-page-token"
        body = http_request.read().decode("utf-8", errors="ignore")
        assert 'name="message"' in body
        assert "Launch locally" in body
        assert 'name="source"; filename="upload-0.png"' in body
        return httpx.Response(
            200,
            json={"id": "photo-123", "post_id": "facebook-post-123"},
        )

    transport = httpx.MockTransport(handler)
    adapter = FacebookAdapter(
        client_factory=lambda: httpx.Client(transport=transport, timeout=30.0)
    )

    result = adapter.submit(
        request,
        settings,
        attempted_at=datetime(2026, 4, 18, 20, 0, tzinfo=UTC),
    )

    assert result.status == "posted"
    assert result.external_post_id == "facebook-post-123"
    assert result.posted_at == datetime(2026, 4, 18, 20, 0, tzinfo=UTC)
    assert result.response_summary == json.dumps(
        {"id": "photo-123", "post_id": "facebook-post-123"},
        sort_keys=True,
    )


def test_facebook_adapter_requires_pages_manage_posts_scope(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    request = build_request(settings, media_count=1)
    request = PostingRequest(
        post_id=request.post_id,
        platform_definition=request.platform_definition,
        caption=request.caption,
        hashtags=request.hashtags,
        posting_text=request.posting_text,
        media_items=request.media_items,
        connected_account=PostingConnectedAccount(
            provider_slug="facebook",
            provider_account_id="facebook-page-1",
            display_name="Story Mimic",
            username=None,
            access_token="facebook-page-token",
            refresh_token=None,
            token_type="Bearer",
            scopes=("pages_show_list",),
        ),
    )
    adapter = FacebookAdapter()

    result = adapter.validate(
        request,
        settings,
        attempted_at=datetime(2026, 4, 18, 20, 5, tzinfo=UTC),
    )

    assert result is not None
    assert result.status == "reauthorization_required"
    assert "pages_manage_posts" in (result.error_message or "")


def test_facebook_adapter_rejects_multi_image_submission(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    request = build_request(settings, media_count=2)
    adapter = FacebookAdapter()

    result = adapter.validate(
        request,
        settings,
        attempted_at=datetime(2026, 4, 18, 20, 10, tzinfo=UTC),
    )

    assert result is not None
    assert result.status == "validation_failed"
    assert result.error_message == "Facebook posting currently supports one image only."


def test_facebook_adapter_normalizes_http_failures_to_submission_failed(
    tmp_path: Path,
) -> None:
    settings = build_settings(tmp_path)
    request = build_request(settings, media_count=1)

    def handler(http_request: httpx.Request) -> httpx.Response:
        del http_request
        return httpx.Response(500, text="server error")

    transport = httpx.MockTransport(handler)
    adapter = FacebookAdapter(
        client_factory=lambda: httpx.Client(transport=transport, timeout=30.0)
    )

    result = adapter.submit(
        request,
        settings,
        attempted_at=datetime(2026, 4, 18, 20, 15, tzinfo=UTC),
    )

    assert result.status == "submission_failed"
    assert result.error_message == "Facebook returned HTTP 500."
    assert result.response_summary == "server error"
