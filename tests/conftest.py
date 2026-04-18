from __future__ import annotations

from pathlib import Path

import pytest

from alembic import command
from app.accounts_service import upsert_connected_account
from app.config import Settings, get_settings
from app.db import (
    ConnectedAccount,
    build_alembic_config,
    clear_db_runtime_caches,
    get_session_factory,
)
from app.oauth_clients import OAuthConnectedAccountPayload


@pytest.fixture
def isolated_runtime_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Settings:
    storage_root = tmp_path / "storage"
    uploads_dir = storage_root / "uploads"
    generated_dir = storage_root / "generated"
    database_path = storage_root / "db" / "app.db"

    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("UPLOADS_DIR", str(uploads_dir))
    monkeypatch.setenv("GENERATED_DIR", str(generated_dir))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "")
    monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "")
    monkeypatch.setenv("FACEBOOK_CLIENT_ID", "")
    monkeypatch.setenv("FACEBOOK_CLIENT_SECRET", "")
    monkeypatch.setenv("X_CLIENT_ID", "")

    get_settings.cache_clear()
    clear_db_runtime_caches()
    yield get_settings()

    get_settings.cache_clear()
    clear_db_runtime_caches()


@pytest.fixture
def isolated_local_runtime(isolated_runtime_settings: Settings) -> Path:
    settings = isolated_runtime_settings
    for path in settings.local_storage_paths:
        path.mkdir(parents=True, exist_ok=True)

    command.upgrade(build_alembic_config(settings), "head")

    return settings.storage_root_path


@pytest.fixture
def configure_platform_env(monkeypatch: pytest.MonkeyPatch):
    def _configure(
        *,
        instagram: bool = False,
        facebook: bool = False,
        x: bool = False,
        x_posting: bool = False,
    ) -> None:
        if instagram:
            monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test-instagram-client")
            monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test-instagram-secret")
        else:
            monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "")
            monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "")

        if facebook:
            monkeypatch.setenv("FACEBOOK_CLIENT_ID", "test-facebook-client")
            monkeypatch.setenv("FACEBOOK_CLIENT_SECRET", "test-facebook-secret")
        else:
            monkeypatch.setenv("FACEBOOK_CLIENT_ID", "")
            monkeypatch.setenv("FACEBOOK_CLIENT_SECRET", "")

        if x or x_posting:
            monkeypatch.setenv("X_CLIENT_ID", "test-x-client")
        else:
            monkeypatch.setenv("X_CLIENT_ID", "")

        get_settings.cache_clear()
        clear_db_runtime_caches()
        settings = get_settings()

        session_factory = get_session_factory(settings)
        with session_factory() as session:
            session.query(ConnectedAccount).delete()
            session.commit()

            if instagram:
                upsert_connected_account(
                    session,
                    OAuthConnectedAccountPayload(
                        provider_slug="instagram",
                        provider_account_id="instagram-user-1",
                        account_type="instagram_professional",
                        display_name="Test Instagram",
                        username="test.instagram",
                        access_token="instagram-access-token",
                        refresh_token=None,
                        token_type="Bearer",
                        scopes=("instagram_business_basic",),
                        expires_at=None,
                        refresh_expires_at=None,
                        provider_metadata={},
                    ),
                )
            if facebook:
                upsert_connected_account(
                    session,
                    OAuthConnectedAccountPayload(
                        provider_slug="facebook",
                        provider_account_id="facebook-page-1",
                        account_type="facebook_page",
                        display_name="Test Facebook Page",
                        username=None,
                        access_token="facebook-page-access-token",
                        refresh_token=None,
                        token_type="Bearer",
                        scopes=("pages_show_list", "pages_manage_posts"),
                        expires_at=None,
                        refresh_expires_at=None,
                        provider_metadata={},
                    ),
                )
            if x or x_posting:
                upsert_connected_account(
                    session,
                    OAuthConnectedAccountPayload(
                        provider_slug="x",
                        provider_account_id="x-user-1",
                        account_type="x_user",
                        display_name="Test X User",
                        username="test_x",
                        access_token="x-access-token",
                        refresh_token="x-refresh-token",
                        token_type="Bearer",
                        scopes=(
                            "tweet.write",
                            "media.write",
                            "users.read",
                            "offline.access",
                        ),
                        expires_at=None,
                        refresh_expires_at=None,
                        provider_metadata={},
                    ),
                )

    return _configure
