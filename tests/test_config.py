from pathlib import Path

import pytest

from app.config import PROJECT_ROOT, Settings


def test_settings_resolve_repo_relative_paths() -> None:
    settings = Settings(
        _env_file=None,
        storage_root=Path("storage"),
        uploads_dir=Path("storage/uploads"),
        generated_dir=Path("storage/generated"),
        database_url="sqlite:///./storage/db/app.db",
    )

    assert settings.project_root == PROJECT_ROOT
    assert settings.storage_root_path == (PROJECT_ROOT / "storage").resolve()
    assert settings.uploads_path == (PROJECT_ROOT / "storage/uploads").resolve()
    assert settings.generated_path == (PROJECT_ROOT / "storage/generated").resolve()
    assert settings.database_path == (PROJECT_ROOT / "storage/db/app.db").resolve()
    assert settings.database_dir == (PROJECT_ROOT / "storage/db").resolve()


def test_settings_reject_non_sqlite_database_url() -> None:
    settings = Settings(_env_file=None, database_url="postgresql://localhost/app")

    with pytest.raises(ValueError, match="Only local SQLite database URLs"):
        _ = settings.database_path
