from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local-First Social Publisher"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = "sqlite:///./storage/db/app.db"
    storage_root: Path = Path("storage")
    uploads_dir: Path = Path("storage/uploads")
    generated_dir: Path = Path("storage/generated")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path:
        sqlite_prefix = "sqlite:///"
        if not self.database_url.startswith(sqlite_prefix):
            raise ValueError("Only local SQLite database URLs are supported.")
        return Path(self.database_url.removeprefix(sqlite_prefix))

    @property
    def local_storage_paths(self) -> tuple[Path, ...]:
        return (
            self.storage_root,
            self.uploads_dir,
            self.generated_dir,
            self.database_path.parent,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
