from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, select, text

from alembic import command
from app.config import PROJECT_ROOT, Settings
from app.db import (
    Base,
    MediaItem,
    Post,
    PostPlatformLog,
    clear_db_runtime_caches,
    get_engine,
    get_session_factory,
)


def build_test_settings(database_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{database_path}",
    )


def test_sqlite_runtime_enables_foreign_keys(tmp_path: Path) -> None:
    clear_db_runtime_caches()
    settings = build_test_settings(tmp_path / "runtime.db")
    engine = get_engine(settings)

    with engine.connect() as connection:
        enabled = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

    assert enabled == 1


def test_post_model_round_trip_preserves_order_and_cascades(tmp_path: Path) -> None:
    clear_db_runtime_caches()
    settings = build_test_settings(tmp_path / "models.db")
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(settings)

    with session_factory() as session:
        post = Post(
            caption="Ship it",
            hashtags="#local #sqlite",
            media_items=[
                MediaItem(
                    file_path="uploads/second.png",
                    media_type="image",
                    original_filename="second.png",
                    width=1200,
                    height=1200,
                    display_order=1,
                ),
                MediaItem(
                    file_path="uploads/first.png",
                    media_type="image",
                    original_filename="first.png",
                    width=1200,
                    height=1200,
                    display_order=0,
                ),
            ],
            post_platform_logs=[
                PostPlatformLog(platform_slug="instagram", status="pending"),
                PostPlatformLog(
                    platform_slug="x",
                    status="submission_failed",
                    error_message="API key missing",
                    response_summary='{"detail":"missing"}',
                ),
            ],
        )
        session.add(post)
        session.commit()
        post_id = post.id

    with session_factory() as session:
        loaded_post = session.scalar(select(Post).where(Post.id == post_id))

        assert loaded_post is not None
        assert [item.display_order for item in loaded_post.media_items] == [0, 1]
        assert [item.file_path for item in loaded_post.media_items] == [
            "uploads/first.png",
            "uploads/second.png",
        ]
        assert {log.platform_slug for log in loaded_post.post_platform_logs} == {
            "instagram",
            "x",
        }

        session.execute(
            text("DELETE FROM posts WHERE id = :post_id"), {"post_id": post_id}
        )
        session.commit()

        remaining_media = session.execute(
            text("SELECT COUNT(*) FROM media_items"),
        ).scalar_one()
        remaining_logs = session.execute(
            text("SELECT COUNT(*) FROM post_platform_logs"),
        ).scalar_one()

    assert remaining_media == 0
    assert remaining_logs == 0


def test_post_updated_at_changes_when_row_is_modified(tmp_path: Path) -> None:
    clear_db_runtime_caches()
    settings = build_test_settings(tmp_path / "timestamps.db")
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(settings)

    with session_factory() as session:
        post = Post(caption="Before", hashtags="#phase4")
        session.add(post)
        session.commit()
        original_updated_at = post.updated_at

        post.caption = "After"
        session.commit()

        assert post.updated_at > original_updated_at


def test_alembic_upgrade_creates_phase_nine_schema(tmp_path: Path) -> None:
    clear_db_runtime_caches()
    database_path = tmp_path / "migrated.db"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["database_url"] = f"sqlite:///{database_path}"
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))

    command.upgrade(config, "head")

    engine = get_engine(build_test_settings(database_path))
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "connected_accounts",
        "media_items",
        "oauth_connection_attempts",
        "post_platform_logs",
        "posts",
    }
    assert {column["name"] for column in inspector.get_columns("posts")} == {
        "id",
        "caption",
        "hashtags",
        "created_at",
        "updated_at",
    }
    assert {column["name"] for column in inspector.get_columns("media_items")} == {
        "id",
        "post_id",
        "file_path",
        "media_type",
        "original_filename",
        "width",
        "height",
        "display_order",
        "created_at",
    }
    assert {
        column["name"] for column in inspector.get_columns("post_platform_logs")
    } == {
        "id",
        "post_id",
        "platform_slug",
        "status",
        "created_at",
        "posted_at",
        "external_post_id",
        "account_display_name",
        "account_identifier",
        "error_message",
        "response_summary",
    }
    assert {
        column["name"] for column in inspector.get_columns("connected_accounts")
    } == {
        "id",
        "provider_slug",
        "provider_account_id",
        "account_type",
        "display_name",
        "username",
        "access_token",
        "refresh_token",
        "token_type",
        "scopes",
        "expires_at",
        "refresh_expires_at",
        "connection_status",
        "provider_metadata_json",
        "last_validated_at",
        "last_used_at",
        "created_at",
        "updated_at",
    }
    assert {
        column["name"] for column in inspector.get_columns("oauth_connection_attempts")
    } == {
        "id",
        "provider_slug",
        "state_token",
        "code_verifier",
        "pending_payload_json",
        "redirect_after",
        "expires_at",
        "created_at",
    }
    assert {index["name"] for index in inspector.get_indexes("post_platform_logs")} >= {
        "ix_post_platform_logs_post_id",
        "ix_post_platform_logs_post_id_platform_slug_created_at",
    }
    assert (
        inspector.get_foreign_keys("media_items")[0]["options"]["ondelete"] == "CASCADE"
    )
    assert (
        inspector.get_foreign_keys("post_platform_logs")[0]["options"]["ondelete"]
        == "CASCADE"
    )

    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version"),
        ).scalar_one()

    assert revision == "5b4f87dd0b9c"
