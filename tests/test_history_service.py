from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from app.config import Settings
from app.db import (
    Base,
    MediaItem,
    Post,
    PostPlatformLog,
    clear_db_runtime_caches,
    get_engine,
    get_session_factory,
)
from app.history_service import (
    build_post_format_label,
    load_history_index_state,
    load_post_history_state,
    summarize_caption,
)


def build_test_settings(tmp_path: Path) -> Settings:
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
    )


def save_upload(
    settings: Settings,
    *,
    post_id: int,
    display_order: int,
    size: tuple[int, int] = (48, 36),
) -> str:
    relative_path = (
        Path("uploads") / "posts" / str(post_id) / f"{display_order:03d}-history.png"
    )
    absolute_path = settings.storage_root_path / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(90, 60, 40)).save(absolute_path, format="PNG")
    return relative_path.as_posix()


def test_history_index_state_empty_when_no_posts(tmp_path: Path) -> None:
    clear_db_runtime_caches()
    settings = build_test_settings(tmp_path)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(settings)

    with session_factory() as session:
        state = load_history_index_state(session, settings=settings)

    assert state.has_posts is False
    assert state.posts == ()


def test_history_index_state_lists_posts_newest_first_with_latest_outcomes(
    tmp_path: Path,
) -> None:
    clear_db_runtime_caches()
    settings = build_test_settings(tmp_path)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(settings)

    with session_factory() as session:
        older_post = Post(
            caption="Older saved caption",
            hashtags="#older",
            created_at=datetime(2026, 4, 16, 9, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 16, 9, 0, tzinfo=UTC),
        )
        newer_post = Post(
            caption="Newer saved caption",
            hashtags="#newer",
            created_at=datetime(2026, 4, 17, 9, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 17, 9, 0, tzinfo=UTC),
        )
        session.add_all([older_post, newer_post])
        session.flush()

        older_post.media_items.append(
            MediaItem(
                file_path=save_upload(settings, post_id=older_post.id, display_order=0),
                media_type="image",
                original_filename="older.png",
                width=48,
                height=36,
                display_order=0,
            )
        )
        newer_post.media_items.extend(
            [
                MediaItem(
                    file_path=save_upload(
                        settings,
                        post_id=newer_post.id,
                        display_order=0,
                    ),
                    media_type="image",
                    original_filename="newer-1.png",
                    width=48,
                    height=36,
                    display_order=0,
                ),
                MediaItem(
                    file_path=save_upload(
                        settings,
                        post_id=newer_post.id,
                        display_order=1,
                        size=(36, 48),
                    ),
                    media_type="image",
                    original_filename="newer-2.png",
                    width=36,
                    height=48,
                    display_order=1,
                ),
            ]
        )
        newer_post.post_platform_logs.extend(
            [
                PostPlatformLog(
                    platform_slug="x",
                    status="posted",
                    created_at=datetime(2026, 4, 17, 9, 5, tzinfo=UTC),
                    posted_at=datetime(2026, 4, 17, 9, 5, tzinfo=UTC),
                    external_post_id="tweet-1",
                ),
                PostPlatformLog(
                    platform_slug="instagram",
                    status="unsupported",
                    created_at=datetime(2026, 4, 17, 9, 4, tzinfo=UTC),
                    error_message="Deferred provider.",
                ),
            ]
        )
        session.commit()

    with session_factory() as session:
        state = load_history_index_state(session, settings=settings)

    assert state.has_posts is True
    assert [post.post_id for post in state.posts] == [newer_post.id, older_post.id]
    assert state.posts[0].format_label == "Image carousel · 2 items"
    assert state.posts[0].first_media_item is not None
    assert [outcome.platform_slug for outcome in state.posts[0].latest_outcomes] == [
        "x",
        "instagram",
    ]
    assert state.posts[1].latest_outcomes == ()


def test_post_history_state_includes_ordered_media_and_full_attempt_history(
    tmp_path: Path,
) -> None:
    clear_db_runtime_caches()
    settings = build_test_settings(tmp_path)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(settings)

    with session_factory() as session:
        post = Post(
            caption="Ledger caption",
            hashtags="#ledger",
            created_at=datetime(2026, 4, 17, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 17, 12, 0, tzinfo=UTC),
            media_items=[
                MediaItem(
                    file_path=save_upload(settings, post_id=1, display_order=0),
                    media_type="image",
                    original_filename="first.png",
                    width=48,
                    height=36,
                    display_order=0,
                ),
                MediaItem(
                    file_path=save_upload(
                        settings,
                        post_id=1,
                        display_order=1,
                        size=(36, 48),
                    ),
                    media_type="image",
                    original_filename="second.png",
                    width=36,
                    height=48,
                    display_order=1,
                ),
            ],
            post_platform_logs=[
                PostPlatformLog(
                    platform_slug="x",
                    status="submission_failed",
                    created_at=datetime(2026, 4, 17, 12, 5, tzinfo=UTC),
                    error_message="Provider timeout.",
                ),
                PostPlatformLog(
                    platform_slug="x",
                    status="posted",
                    created_at=datetime(2026, 4, 17, 12, 8, tzinfo=UTC),
                    posted_at=datetime(2026, 4, 17, 12, 8, tzinfo=UTC),
                    external_post_id="tweet-2",
                ),
                PostPlatformLog(
                    platform_slug="instagram",
                    status="unsupported",
                    created_at=datetime(2026, 4, 17, 12, 6, tzinfo=UTC),
                    error_message="Deferred provider.",
                ),
            ],
        )
        session.add(post)
        session.commit()
        post_id = post.id

    with session_factory() as session:
        state = load_post_history_state(session, post_id=post_id, settings=settings)

    assert state is not None
    assert state.post_summary.media_count == 2
    assert [item.display_order for item in state.media_items] == [0, 1]
    assert [attempt.platform_slug for attempt in state.attempt_history] == [
        "x",
        "instagram",
        "x",
    ]
    assert [outcome.platform_slug for outcome in state.latest_outcomes] == [
        "x",
        "instagram",
    ]
    assert state.latest_outcomes[0].external_post_id == "tweet-2"


def test_history_helpers_return_expected_labels() -> None:
    assert summarize_caption("A" * 140, "#hash") == ("A" * 119) + "…"
    assert summarize_caption("", "#hash") == "#hash"
    assert build_post_format_label(1) == "Single image"
    assert build_post_format_label(3) == "Image carousel · 3 items"
