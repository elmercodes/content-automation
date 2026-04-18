from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from alembic import command
from app.config import Settings
from app.db import (
    build_alembic_config,
    clear_db_runtime_caches,
    get_engine,
)
from app.main import create_app

EXPECTED_ENV_KEYS = {
    "APP_ENV",
    "APP_HOST",
    "APP_PORT",
    "APP_BASE_URL",
    "DATABASE_URL",
    "STORAGE_ROOT",
    "UPLOADS_DIR",
    "GENERATED_DIR",
    "INSTAGRAM_CLIENT_ID",
    "INSTAGRAM_CLIENT_SECRET",
    "FACEBOOK_CLIENT_ID",
    "FACEBOOK_CLIENT_SECRET",
    "META_API_VERSION",
    "X_CLIENT_ID",
}
HEAD_REVISION = "5b4f87dd0b9c"
PRE_OAUTH_REVISION = "4f7d2c10c8a8"


@pytest.mark.anyio
async def test_app_lifespan_creates_local_storage_directories(
    isolated_runtime_settings: Settings,
) -> None:
    settings = isolated_runtime_settings

    assert all(not path.exists() for path in settings.local_storage_paths)

    app = create_app()
    async with app.router.lifespan_context(app):
        pass

    assert all(path.exists() for path in settings.local_storage_paths)

    clear_db_runtime_caches()
    engine = get_engine(settings)
    inspector = inspect(engine)
    assert "oauth_connection_attempts" in inspector.get_table_names()

    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version"),
        ).scalar_one()

    assert revision == HEAD_REVISION


@pytest.mark.anyio
async def test_app_lifespan_upgrades_existing_local_db_to_head(
    isolated_runtime_settings: Settings,
) -> None:
    settings = isolated_runtime_settings
    for path in settings.local_storage_paths:
        path.mkdir(parents=True, exist_ok=True)

    command.upgrade(build_alembic_config(settings), PRE_OAUTH_REVISION)

    clear_db_runtime_caches()
    engine = get_engine(settings)
    inspector = inspect(engine)
    assert "oauth_connection_attempts" not in inspector.get_table_names()

    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version"),
        ).scalar_one()

    assert revision == PRE_OAUTH_REVISION

    app = create_app()
    async with app.router.lifespan_context(app):
        pass

    clear_db_runtime_caches()
    engine = get_engine(settings)
    inspector = inspect(engine)
    assert "oauth_connection_attempts" in inspector.get_table_names()

    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version"),
        ).scalar_one()

    assert revision == HEAD_REVISION


def test_env_example_includes_current_runtime_and_provider_settings() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")
    env_keys = {
        match.group(1)
        for match in re.finditer(
            r"^\s*#?\s*([A-Z][A-Z0-9_]+)=", env_example, re.MULTILINE
        )
    }

    assert EXPECTED_ENV_KEYS.issubset(env_keys)
