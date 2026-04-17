"""Shared posting adapter types and adapter resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.platforms.registry import PlatformDefinition, get_platform


@dataclass(frozen=True, slots=True)
class PostingMediaItem:
    display_order: int
    original_filename: str | None
    media_type: str
    width: int | None
    height: int | None
    file_path: str
    absolute_path: Path

    @property
    def label(self) -> str:
        return self.original_filename or self.absolute_path.name


@dataclass(frozen=True, slots=True)
class PostingRequest:
    post_id: int
    platform_definition: PlatformDefinition
    caption: str
    hashtags: str
    posting_text: str
    media_items: tuple[PostingMediaItem, ...]

    @property
    def platform_slug(self) -> str:
        return self.platform_definition.slug

    @property
    def platform_display_name(self) -> str:
        return self.platform_definition.display_name

    @property
    def media_count(self) -> int:
        return len(self.media_items)

    @property
    def is_carousel(self) -> bool:
        return self.media_count > 1


@dataclass(frozen=True, slots=True)
class PostingResult:
    platform_slug: str
    status: str
    attempted_at: datetime
    external_post_id: str | None = None
    error_message: str | None = None
    response_summary: str | None = None
    posted_at: datetime | None = None


class PlatformAdapter(Protocol):
    def validate(
        self,
        request: PostingRequest,
        settings: Settings,
        *,
        attempted_at: datetime,
    ) -> PostingResult | None: ...

    def submit(
        self,
        request: PostingRequest,
        settings: Settings,
        *,
        attempted_at: datetime,
    ) -> PostingResult: ...


class UnsupportedPlatformAdapter:
    """Deterministic adapter used when direct posting is intentionally deferred."""

    def __init__(self, platform_slug: str) -> None:
        self.platform_slug = platform_slug

    def validate(
        self,
        request: PostingRequest,
        settings: Settings,
        *,
        attempted_at: datetime,
    ) -> PostingResult:
        del settings
        notes = request.platform_definition.posting_spec.notes or (
            f"{request.platform_display_name} posting is not available yet."
        )
        return PostingResult(
            platform_slug=request.platform_slug,
            status="unsupported",
            attempted_at=attempted_at,
            error_message=notes,
        )

    def submit(
        self,
        request: PostingRequest,
        settings: Settings,
        *,
        attempted_at: datetime,
    ) -> PostingResult:
        return self.validate(request, settings, attempted_at=attempted_at)


def resolve_platform_adapter(platform_slug: str) -> PlatformAdapter:
    if platform_slug == "x":
        from app.platforms.x_adapter import XAdapter

        return XAdapter()

    get_platform(platform_slug)
    return UnsupportedPlatformAdapter(platform_slug)
