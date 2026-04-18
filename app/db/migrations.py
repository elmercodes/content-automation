"""Alembic helpers for keeping the local SQLite schema current."""

from __future__ import annotations

from alembic.config import Config

from alembic import command
from app.config import PROJECT_ROOT, Settings, get_settings
from app.db.session import clear_db_runtime_caches


class DatabaseMigrationError(RuntimeError):
    """Raised when the local database schema cannot be upgraded."""


def build_alembic_config(settings: Settings | None = None) -> Config:
    resolved_settings = settings or get_settings()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["database_url"] = resolved_settings.database_url
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    return config


def upgrade_database_to_head(settings: Settings | None = None) -> None:
    resolved_settings = settings or get_settings()
    database_path = resolved_settings.database_path
    try:
        command.upgrade(build_alembic_config(resolved_settings), "head")
    except Exception as exc:
        raise DatabaseMigrationError(
            "Could not upgrade the local SQLite schema at "
            f"{database_path}. Run `.venv/bin/alembic upgrade head` and "
            "restart the app."
        ) from exc

    clear_db_runtime_caches()
