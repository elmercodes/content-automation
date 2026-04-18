from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from alembic import command
from app import accounts_service
from app.config import get_settings
from app.db import (
    OAuthConnectionAttempt,
    build_alembic_config,
    clear_db_runtime_caches,
    get_engine,
    get_session_factory,
)
from app.main import create_app
from app.oauth_clients import FacebookUserAuthorization, OAuthProviderError

HEAD_REVISION = "5b4f87dd0b9c"
PRE_OAUTH_REVISION = "4f7d2c10c8a8"


@pytest.mark.anyio
async def test_connect_provider_upgrades_old_db_before_creating_oauth_attempt(
    isolated_runtime_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test-instagram-client")
    monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test-instagram-secret")

    get_settings.cache_clear()
    clear_db_runtime_caches()
    settings = get_settings()
    for path in settings.local_storage_paths:
        path.mkdir(parents=True, exist_ok=True)

    command.upgrade(build_alembic_config(settings), PRE_OAUTH_REVISION)

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get("/connect/instagram", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith(
        "https://www.instagram.com/oauth/authorize?"
    )

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        attempts = session.scalars(select(OAuthConnectionAttempt)).all()

    assert len(attempts) == 1
    assert attempts[0].provider_slug == "instagram"

    clear_db_runtime_caches()
    engine = get_engine(settings)
    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version"),
        ).scalar_one()

    assert revision == HEAD_REVISION


@pytest.mark.anyio
async def test_facebook_callback_redirects_to_accounts_when_page_lookup_fails(
    isolated_local_runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    session_factory = get_session_factory(settings)
    with session_factory() as session:
        attempt = accounts_service.create_oauth_connection_attempt(
            session,
            provider_slug="facebook",
            redirect_after=str(settings.app_base_url),
        )

    class FailingFacebookClient:
        provider_slug = "facebook"
        supports_pkce = False
        supports_refresh = False

        def exchange_code(
            self,
            *,
            settings,
            callback_url,
            code,
            code_verifier=None,
        ):
            del settings, callback_url, code, code_verifier
            return FacebookUserAuthorization(
                access_token="facebook-user-token",
                token_type="Bearer",
                scopes=("pages_show_list",),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                user_id="facebook-user-1",
                user_name="Test User",
            )

        def load_page_options(self, *, settings, authorization):
            del settings, authorization
            raise OAuthProviderError("Facebook Page lookup failed.")

    monkeypatch.setattr(
        "app.web.routes.accounts.get_oauth_client",
        lambda provider_slug: FailingFacebookClient(),
    )

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="https://localhost:8000",
        ) as client:
            response = await client.get(
                f"/oauth/callback/facebook?state={attempt.state_token}&code=test-code",
                follow_redirects=False,
            )

    assert response.status_code == 303
    assert (
        "/accounts?error=Facebook+Page+lookup+failed." in response.headers["location"]
    )

    with session_factory() as session:
        attempts = session.scalars(select(OAuthConnectionAttempt)).all()

    assert attempts == []
