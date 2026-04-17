"""Read-side history and results state assembly for stored master posts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.db import Post, PostPlatformLog
from app.platform_selection_service import (
    WorkflowMasterPostSummary,
    WorkflowMediaItemSummary,
)
from app.platforms import get_platform
from app.presentation import format_display_datetime

STATUS_VARIANT_MAP = {
    "pending": "info",
    "posted": "success",
    "not_configured": "warning",
    "unsupported": "warning",
    "validation_failed": "error",
    "submission_failed": "error",
}


@dataclass(frozen=True, slots=True)
class StatusPresentation:
    status: str
    label: str
    variant: str


@dataclass(frozen=True, slots=True)
class PlatformOutcomeSummary:
    platform_slug: str
    platform_display_name: str
    status: str
    status_label: str
    status_variant: str
    attempted_at: datetime
    posted_at: datetime | None
    external_post_id: str | None
    account_display_name: str | None
    account_identifier: str | None
    error_message: str | None
    response_summary: str | None

    @property
    def attempted_at_display(self) -> str:
        return format_display_datetime(self.attempted_at)

    @property
    def posted_at_display(self) -> str | None:
        if self.posted_at is None:
            return None
        return format_display_datetime(self.posted_at)


@dataclass(frozen=True, slots=True)
class PlatformAttemptSummary:
    platform_slug: str
    platform_display_name: str
    status: str
    status_label: str
    status_variant: str
    attempted_at: datetime
    posted_at: datetime | None
    external_post_id: str | None
    account_display_name: str | None
    account_identifier: str | None
    error_message: str | None
    response_summary: str | None

    @property
    def attempted_at_display(self) -> str:
        return format_display_datetime(self.attempted_at)

    @property
    def posted_at_display(self) -> str | None:
        if self.posted_at is None:
            return None
        return format_display_datetime(self.posted_at)


@dataclass(frozen=True, slots=True)
class HistoryMediaItemSummary:
    display_order: int
    original_filename: str | None
    media_type: str
    width: int | None
    height: int | None
    file_path: str
    upload_relative_path: str | None
    file_missing: bool

    @property
    def label(self) -> str:
        if self.original_filename:
            return self.original_filename
        return Path(self.file_path).name


@dataclass(frozen=True, slots=True)
class HistoryPostListItem:
    post_id: int
    created_at: datetime
    caption: str
    hashtags: str
    caption_summary: str
    media_count: int
    format_label: str
    first_media_item: HistoryMediaItemSummary | None
    latest_outcomes: tuple[PlatformOutcomeSummary, ...]
    latest_activity_at: datetime | None
    has_attempts: bool

    @property
    def created_at_display(self) -> str:
        return format_display_datetime(self.created_at)

    @property
    def latest_activity_at_display(self) -> str | None:
        if self.latest_activity_at is None:
            return None
        return format_display_datetime(self.latest_activity_at)


@dataclass(frozen=True, slots=True)
class HistoryIndexPageState:
    posts: tuple[HistoryPostListItem, ...]

    @property
    def has_posts(self) -> bool:
        return bool(self.posts)


@dataclass(frozen=True, slots=True)
class SubmissionResultsPageState:
    post_summary: WorkflowMasterPostSummary
    media_items: tuple[HistoryMediaItemSummary, ...]
    latest_outcomes: tuple[PlatformOutcomeSummary, ...]

    @property
    def has_results(self) -> bool:
        return bool(self.latest_outcomes)


@dataclass(frozen=True, slots=True)
class PostHistoryPageState:
    post_summary: WorkflowMasterPostSummary
    created_at: datetime
    media_items: tuple[HistoryMediaItemSummary, ...]
    latest_outcomes: tuple[PlatformOutcomeSummary, ...]
    attempt_history: tuple[PlatformAttemptSummary, ...]

    @property
    def has_attempts(self) -> bool:
        return bool(self.attempt_history)

    @property
    def created_at_display(self) -> str:
        return format_display_datetime(self.created_at)


def load_results_page_state(
    session: Session,
    *,
    post_id: int,
    selected_platform_slugs: tuple[str, ...] = (),
    settings: Settings | None = None,
) -> SubmissionResultsPageState | None:
    resolved_settings = settings or get_settings()
    post = _load_post_with_relationships(session, post_id=post_id)
    if post is None:
        return None

    media_items = _build_history_media_items(post, settings=resolved_settings)
    latest_outcomes = _build_latest_platform_outcomes(
        post.post_platform_logs,
        selected_platform_slugs=selected_platform_slugs,
    )
    return SubmissionResultsPageState(
        post_summary=_build_workflow_post_summary(post),
        media_items=media_items,
        latest_outcomes=latest_outcomes,
    )


def load_history_index_state(
    session: Session,
    *,
    settings: Settings | None = None,
) -> HistoryIndexPageState:
    resolved_settings = settings or get_settings()
    posts = session.scalars(
        select(Post)
        .options(
            selectinload(Post.media_items),
            selectinload(Post.post_platform_logs),
        )
        .order_by(Post.created_at.desc(), Post.id.desc())
    ).all()

    post_items = tuple(
        _build_history_post_list_item(post, settings=resolved_settings)
        for post in posts
    )
    return HistoryIndexPageState(posts=post_items)


def load_post_history_state(
    session: Session,
    *,
    post_id: int,
    settings: Settings | None = None,
) -> PostHistoryPageState | None:
    resolved_settings = settings or get_settings()
    post = _load_post_with_relationships(session, post_id=post_id)
    if post is None:
        return None

    media_items = _build_history_media_items(post, settings=resolved_settings)
    latest_outcomes = _build_latest_platform_outcomes(post.post_platform_logs)
    attempt_history = tuple(
        _build_platform_attempt_summary(log)
        for log in sorted(
            post.post_platform_logs,
            key=lambda log: (log.created_at, log.id),
            reverse=True,
        )
    )
    return PostHistoryPageState(
        post_summary=_build_workflow_post_summary(post),
        created_at=post.created_at,
        media_items=media_items,
        latest_outcomes=latest_outcomes,
        attempt_history=attempt_history,
    )


def present_status(status: str) -> StatusPresentation:
    return StatusPresentation(
        status=status,
        label=status.replace("_", " ").title(),
        variant=STATUS_VARIANT_MAP.get(status, "info"),
    )


def summarize_caption(caption: str, hashtags: str, *, limit: int = 120) -> str:
    summary_source = caption.strip() or hashtags.strip() or "Untitled local post"
    if len(summary_source) <= limit:
        return summary_source
    return f"{summary_source[: limit - 1].rstrip()}…"


def build_post_format_label(media_count: int) -> str:
    if media_count > 1:
        return f"Image carousel · {media_count} items"
    if media_count == 1:
        return "Single image"
    return "No media"


def _load_post_with_relationships(session: Session, *, post_id: int) -> Post | None:
    return session.scalar(
        select(Post)
        .options(
            selectinload(Post.media_items),
            selectinload(Post.post_platform_logs),
        )
        .where(Post.id == post_id)
    )


def _build_history_post_list_item(
    post: Post,
    *,
    settings: Settings,
) -> HistoryPostListItem:
    media_items = _build_history_media_items(post, settings=settings)
    latest_outcomes = _build_latest_platform_outcomes(post.post_platform_logs)
    latest_activity_at = latest_outcomes[0].attempted_at if latest_outcomes else None
    return HistoryPostListItem(
        post_id=post.id,
        created_at=post.created_at,
        caption=post.caption,
        hashtags=post.hashtags,
        caption_summary=summarize_caption(post.caption, post.hashtags),
        media_count=len(post.media_items),
        format_label=build_post_format_label(len(post.media_items)),
        first_media_item=media_items[0] if media_items else None,
        latest_outcomes=latest_outcomes,
        latest_activity_at=latest_activity_at,
        has_attempts=bool(post.post_platform_logs),
    )


def _build_history_media_items(
    post: Post,
    *,
    settings: Settings,
) -> tuple[HistoryMediaItemSummary, ...]:
    return tuple(
        HistoryMediaItemSummary(
            display_order=media_item.display_order,
            original_filename=media_item.original_filename,
            media_type=media_item.media_type,
            width=media_item.width,
            height=media_item.height,
            file_path=media_item.file_path,
            upload_relative_path=_build_upload_relative_path(media_item.file_path),
            file_missing=not (
                settings.storage_root_path / media_item.file_path
            ).is_file(),
        )
        for media_item in post.media_items
    )


def _build_latest_platform_outcomes(
    logs: list[PostPlatformLog],
    *,
    selected_platform_slugs: tuple[str, ...] = (),
) -> tuple[PlatformOutcomeSummary, ...]:
    ordered_platform_slugs = (
        tuple(dict.fromkeys(selected_platform_slugs))
        if selected_platform_slugs
        else tuple(dict.fromkeys(log.platform_slug for log in logs))
    )
    selected_lookup = set(ordered_platform_slugs)
    latest_logs: dict[str, PostPlatformLog] = {}
    for log in logs:
        if selected_lookup and log.platform_slug not in selected_lookup:
            continue
        current = latest_logs.get(log.platform_slug)
        if current is None or (
            log.created_at,
            log.id,
        ) > (current.created_at, current.id):
            latest_logs[log.platform_slug] = log

    outcomes = [
        _build_platform_outcome_summary(latest_logs[platform_slug])
        for platform_slug in ordered_platform_slugs
        if platform_slug in latest_logs
    ]
    return tuple(
        sorted(
            outcomes,
            key=lambda outcome: (outcome.attempted_at, outcome.platform_display_name),
            reverse=True,
        )
    )


def _build_platform_outcome_summary(log: PostPlatformLog) -> PlatformOutcomeSummary:
    status_presentation = present_status(log.status)
    return PlatformOutcomeSummary(
        platform_slug=log.platform_slug,
        platform_display_name=_get_platform_display_name(log.platform_slug),
        status=log.status,
        status_label=status_presentation.label,
        status_variant=status_presentation.variant,
        attempted_at=log.created_at,
        posted_at=log.posted_at,
        external_post_id=log.external_post_id,
        account_display_name=log.account_display_name,
        account_identifier=log.account_identifier,
        error_message=log.error_message,
        response_summary=log.response_summary,
    )


def _build_platform_attempt_summary(log: PostPlatformLog) -> PlatformAttemptSummary:
    status_presentation = present_status(log.status)
    return PlatformAttemptSummary(
        platform_slug=log.platform_slug,
        platform_display_name=_get_platform_display_name(log.platform_slug),
        status=log.status,
        status_label=status_presentation.label,
        status_variant=status_presentation.variant,
        attempted_at=log.created_at,
        posted_at=log.posted_at,
        external_post_id=log.external_post_id,
        account_display_name=log.account_display_name,
        account_identifier=log.account_identifier,
        error_message=log.error_message,
        response_summary=log.response_summary,
    )


def _build_workflow_post_summary(post: Post) -> WorkflowMasterPostSummary:
    return WorkflowMasterPostSummary(
        id=post.id,
        caption=post.caption,
        hashtags=post.hashtags,
        media_items=tuple(
            WorkflowMediaItemSummary(
                display_order=media_item.display_order,
                original_filename=media_item.original_filename,
                media_type=media_item.media_type,
                width=media_item.width,
                height=media_item.height,
                file_path=media_item.file_path,
            )
            for media_item in post.media_items
        ),
    )


def _get_platform_display_name(platform_slug: str) -> str:
    try:
        return get_platform(platform_slug).display_name
    except KeyError:
        return platform_slug


def _build_upload_relative_path(file_path: str) -> str | None:
    path = Path(file_path)
    try:
        uploads_relative_path = path.relative_to("uploads")
    except ValueError:
        return None
    return uploads_relative_path.as_posix()
