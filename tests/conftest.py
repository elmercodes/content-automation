from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.accounts_service import upsert_connected_account
from app.config import PROJECT_ROOT, get_settings
from app.db import ConnectedAccount, clear_db_runtime_caches, get_session_factory
from app.oauth_clients import OAuthConnectedAccountPayload


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
    monkeypatch.delenv("INSTAGRAM_CLIENT_ID", raising=False)
    monkeypatch.delenv("INSTAGRAM_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("FACEBOOK_CLIENT_ID", raising=False)
    monkeypatch.delenv("FACEBOOK_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("X_CLIENT_ID", raising=False)

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
        x_posting: bool = False,
    ) -> None:
        if instagram:
            monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test-instagram-client")
            monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test-instagram-secret")
        else:
            monkeypatch.delenv("INSTAGRAM_CLIENT_ID", raising=False)
            monkeypatch.delenv("INSTAGRAM_CLIENT_SECRET", raising=False)

        if facebook:
            monkeypatch.setenv("FACEBOOK_CLIENT_ID", "test-facebook-client")
            monkeypatch.setenv("FACEBOOK_CLIENT_SECRET", "test-facebook-secret")
        else:
            monkeypatch.delenv("FACEBOOK_CLIENT_ID", raising=False)
            monkeypatch.delenv("FACEBOOK_CLIENT_SECRET", raising=False)

        if x or x_posting:
            monkeypatch.setenv("X_CLIENT_ID", "test-x-client")
        else:
            monkeypatch.delenv("X_CLIENT_ID", raising=False)

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
                        scopes=("pages_show_list",),
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
