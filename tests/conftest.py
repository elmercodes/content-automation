from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.config import PROJECT_ROOT, get_settings
from app.db import clear_db_runtime_caches


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
        x_posting: bool = False,
    ) -> None:
        if instagram:
            monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "test-instagram-token")
        else:
            monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)

        if facebook:
            monkeypatch.setenv("FACEBOOK_PAGE_ID", "test-facebook-page")
        else:
            monkeypatch.delenv("FACEBOOK_PAGE_ID", raising=False)

        if x or x_posting:
            monkeypatch.setenv("X_API_KEY", "test-x-key")
        else:
            monkeypatch.delenv("X_API_KEY", raising=False)

        if x_posting:
            monkeypatch.setenv("X_API_SECRET", "test-x-secret")
            monkeypatch.setenv("X_ACCESS_TOKEN", "test-x-access-token")
            monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "test-x-access-token-secret")
        else:
            monkeypatch.delenv("X_API_SECRET", raising=False)
            monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)
            monkeypatch.delenv("X_ACCESS_TOKEN_SECRET", raising=False)

        get_settings.cache_clear()
        clear_db_runtime_caches()

    return _configure
