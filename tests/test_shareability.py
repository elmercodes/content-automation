from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.config import get_settings
from app.db import clear_db_runtime_caches
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


@pytest.mark.anyio
async def test_app_lifespan_creates_local_storage_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_root = tmp_path / "storage"
    uploads_dir = storage_root / "uploads"
    generated_dir = storage_root / "generated"
    database_path = storage_root / "db" / "app.db"

    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("UPLOADS_DIR", str(uploads_dir))
    monkeypatch.setenv("GENERATED_DIR", str(generated_dir))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    get_settings.cache_clear()
    clear_db_runtime_caches()
    settings = get_settings()

    assert all(not path.exists() for path in settings.local_storage_paths)

    app = create_app()
    async with app.router.lifespan_context(app):
        pass

    assert all(path.exists() for path in settings.local_storage_paths)


def test_env_example_includes_current_runtime_and_provider_settings() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")
    env_keys = {
        match.group(1)
        for match in re.finditer(
            r"^\s*#?\s*([A-Z][A-Z0-9_]+)=", env_example, re.MULTILINE
        )
    }

    assert EXPECTED_ENV_KEYS.issubset(env_keys)
