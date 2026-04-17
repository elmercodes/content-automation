from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_repo_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


class Settings(BaseSettings):
    app_name: str = "Local-First Social Publisher"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_base_url: str = "http://127.0.0.1:8000"
    database_url: str = "sqlite:///./storage/db/app.db"
    storage_root: Path = Path("storage")
    uploads_dir: Path = Path("storage/uploads")
    generated_dir: Path = Path("storage/generated")
    instagram_client_id: str | None = None
    instagram_client_secret: str | None = None
    facebook_client_id: str | None = None
    facebook_client_secret: str | None = None
    meta_api_version: str = "v23.0"
    x_client_id: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def storage_root_path(self) -> Path:
        return _resolve_repo_path(self.storage_root)

    @property
    def uploads_path(self) -> Path:
        return _resolve_repo_path(self.uploads_dir)

    @property
    def generated_path(self) -> Path:
        return _resolve_repo_path(self.generated_dir)

    @property
    def database_path(self) -> Path:
        sqlite_prefix = "sqlite:///"
        if not self.database_url.startswith(sqlite_prefix):
            raise ValueError("Only local SQLite database URLs are supported.")
        return _resolve_repo_path(Path(self.database_url.removeprefix(sqlite_prefix)))

    @property
    def database_dir(self) -> Path:
        return self.database_path.parent

    @property
    def local_storage_paths(self) -> tuple[Path, ...]:
        paths = (
            self.storage_root_path,
            self.uploads_path,
            self.generated_path,
            self.database_dir,
        )
        return tuple(dict.fromkeys(paths))


@lru_cache
def get_settings() -> Settings:
    return Settings()
