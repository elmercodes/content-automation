"""Runtime engine and session helpers for the local SQLite database."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def _is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


@lru_cache(maxsize=None)
def _build_engine(database_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if _is_sqlite_url(database_url):
        connect_args["check_same_thread"] = False

    engine = create_engine(database_url, connect_args=connect_args)

    if _is_sqlite_url(database_url):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


@lru_cache(maxsize=None)
def _build_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(
        bind=_build_engine(database_url),
        autoflush=False,
        expire_on_commit=False,
    )


def get_engine(settings: Settings | None = None) -> Engine:
    resolved_settings = settings or get_settings()
    return _build_engine(resolved_settings.database_url)


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    resolved_settings = settings or get_settings()
    return _build_session_factory(resolved_settings.database_url)


def get_db_session(settings: Settings | None = None) -> Iterator[Session]:
    session = get_session_factory(settings)()
    try:
        yield session
    finally:
        session.close()


def clear_db_runtime_caches() -> None:
    _build_session_factory.cache_clear()
    _build_engine.cache_clear()
