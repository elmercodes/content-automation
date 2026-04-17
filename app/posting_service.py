"""Posting orchestration and per-platform logging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts_service import (
    ensure_connected_account_active,
    get_provider_runtime_state,
    mark_connected_account_used,
)
from app.config import Settings, get_settings
from app.db import ConnectedAccount, PostPlatformLog
from app.platform_selection_service import (
    PlatformChoice,
    PlatformReviewState,
)
from app.platforms import get_platform
from app.platforms.adapters import (
    PlatformAdapter,
    PostingConnectedAccount,
    PostingMediaItem,
    PostingRequest,
    PostingResult,
    resolve_platform_adapter,
)
from app.preview_service import build_posting_text, build_posting_text_metrics


@dataclass(frozen=True, slots=True)
class PostingReadinessSummary:
    platform: PlatformChoice
    status: str
    message: str

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


class DuplicateSubmissionError(ValueError):
    """Raised when a platform has already posted successfully for one master post."""

    def __init__(self, platform_slugs: tuple[str, ...]) -> None:
        self.platform_slugs = platform_slugs
        platform_label = ", ".join(platform_slugs)
        super().__init__(
            "Successful post platform logs already exist for: "
            f"{platform_label}. Use the existing results instead of reposting."
        )


def build_posting_request(
    session: Session,
    review_state: PlatformReviewState,
    *,
    platform: PlatformChoice,
    settings: Settings | None = None,
) -> PostingRequest:
    resolved_settings = settings or get_settings()
    platform_definition = get_platform(platform.slug)
    runtime_state = get_provider_runtime_state(
        session,
        platform.slug,
        settings=resolved_settings,
    )
    connected_account = None
    if runtime_state.connected:
        account = ensure_connected_account_active(
            session,
            provider_slug=platform.slug,
            settings=resolved_settings,
        )
        if account is not None and account.access_token:
            connected_account = _build_posting_connected_account(account)
    post_summary = review_state.post_summary
    return PostingRequest(
        post_id=post_summary.id,
        platform_definition=platform_definition,
        caption=post_summary.caption,
        hashtags=post_summary.hashtags,
        posting_text=build_posting_text(
            post_summary.caption,
            post_summary.hashtags,
        ),
        media_items=tuple(
            PostingMediaItem(
                display_order=media_item.display_order,
                original_filename=media_item.original_filename,
                media_type=media_item.media_type,
                width=media_item.width,
                height=media_item.height,
                file_path=media_item.file_path,
                absolute_path=(
                    resolved_settings.storage_root_path / media_item.file_path
                ),
            )
            for media_item in post_summary.media_items
        ),
        connected_account=connected_account,
        account_status=runtime_state.connection_status,
        account_message=runtime_state.connection_message,
    )


def build_posting_readiness_summaries(
    session: Session,
    review_state: PlatformReviewState,
    *,
    settings: Settings | None = None,
    adapter_resolver: Callable[[str], PlatformAdapter] | None = None,
) -> tuple[PostingReadinessSummary, ...]:
    resolved_settings = settings or get_settings()
    resolved_adapter_resolver = adapter_resolver or resolve_platform_adapter
    summaries: list[PostingReadinessSummary] = []
    for platform in review_state.selected_platforms:
        request = build_posting_request(
            session,
            review_state,
            platform=platform,
            settings=resolved_settings,
        )
        validation_result = _validate_submission_request(
            request,
            resolved_settings,
            resolved_adapter_resolver(request.platform_slug),
            attempted_at=_utcnow(),
        )
        if validation_result is None:
            message = (
                f"{platform.display_name} is ready for synchronous local submission."
            )
            status = "ready"
        else:
            message = validation_result.error_message or (
                f"{platform.display_name} is not ready for submission."
            )
            status = validation_result.status
        summaries.append(
            PostingReadinessSummary(
                platform=platform,
                status=status,
                message=message,
            )
        )
    return tuple(summaries)


def submit_reviewed_post(
    session: Session,
    review_state: PlatformReviewState,
    *,
    settings: Settings | None = None,
    adapter_resolver: Callable[[str], PlatformAdapter] | None = None,
) -> tuple[PostingResult, ...]:
    resolved_settings = settings or get_settings()
    resolved_adapter_resolver = adapter_resolver or resolve_platform_adapter
    selected_platform_slugs = tuple(
        platform.slug for platform in review_state.selected_platforms
    )
    _guard_against_duplicate_successes(
        session,
        post_id=review_state.post_summary.id,
        platform_slugs=selected_platform_slugs,
    )

    results: list[PostingResult] = []
    for platform in review_state.selected_platforms:
        request = build_posting_request(
            session,
            review_state,
            platform=platform,
            settings=resolved_settings,
        )
        pending_log = PostPlatformLog(
            post_id=request.post_id,
            platform_slug=request.platform_slug,
            status="pending",
        )
        session.add(pending_log)
        session.commit()
        session.refresh(pending_log)

        result = _submit_one_platform(
            request,
            resolved_settings,
            resolved_adapter_resolver(request.platform_slug),
            attempted_at=pending_log.created_at,
        )
        if request.connected_account is not None:
            pending_log.account_display_name = request.connected_account.account_label
            pending_log.account_identifier = (
                request.connected_account.provider_account_id
                or request.connected_account.username
            )
        _apply_posting_result(pending_log, result)
        session.commit()
        if result.status == "posted" and request.connected_account is not None:
            connected_account = ensure_connected_account_active(
                session,
                provider_slug=request.platform_slug,
                settings=resolved_settings,
            )
            if connected_account is not None:
                mark_connected_account_used(session, connected_account)
        results.append(result)

    return tuple(results)


def _submit_one_platform(
    request: PostingRequest,
    settings: Settings,
    adapter: PlatformAdapter,
    *,
    attempted_at: datetime,
) -> PostingResult:
    validation_result = _validate_submission_request(
        request,
        settings,
        adapter,
        attempted_at=attempted_at,
    )
    if validation_result is not None:
        return validation_result

    try:
        return adapter.submit(
            request,
            settings,
            attempted_at=attempted_at,
        )
    except Exception as exc:
        return PostingResult(
            platform_slug=request.platform_slug,
            status="submission_failed",
            attempted_at=attempted_at,
            error_message=(
                f"{request.platform_display_name} submission failed before a "
                "provider response was recorded."
            ),
            response_summary=str(exc),
        )


def _validate_submission_request(
    request: PostingRequest,
    settings: Settings,
    adapter: PlatformAdapter,
    *,
    attempted_at: datetime,
) -> PostingResult | None:
    if request.account_status != "connected":
        return PostingResult(
            platform_slug=request.platform_slug,
            status=request.account_status,
            attempted_at=attempted_at,
            error_message=request.account_message,
        )

    if not request.media_items:
        return PostingResult(
            platform_slug=request.platform_slug,
            status="validation_failed",
            attempted_at=attempted_at,
            error_message="This master post does not have any media items to submit.",
        )

    if any(media_item.media_type != "image" for media_item in request.media_items):
        return PostingResult(
            platform_slug=request.platform_slug,
            status="validation_failed",
            attempted_at=attempted_at,
            error_message="Phase 9 submission supports image media items only.",
        )

    missing_files = [
        media_item.label
        for media_item in request.media_items
        if not media_item.absolute_path.is_file()
    ]
    if missing_files:
        missing_label = ", ".join(missing_files)
        return PostingResult(
            platform_slug=request.platform_slug,
            status="validation_failed",
            attempted_at=attempted_at,
            error_message=f"Local media files are missing: {missing_label}.",
        )

    unreadable_files = [
        media_item.label
        for media_item in request.media_items
        if not _is_readable_file(media_item.absolute_path)
    ]
    if unreadable_files:
        unreadable_label = ", ".join(unreadable_files)
        return PostingResult(
            platform_slug=request.platform_slug,
            status="validation_failed",
            attempted_at=attempted_at,
            error_message=f"Local media files are not readable: {unreadable_label}.",
        )

    text_metrics = build_posting_text_metrics(
        caption=request.caption,
        hashtags=request.hashtags,
        limit=request.platform_definition.caption_limit,
    )
    if text_metrics.over_limit:
        limit = request.platform_definition.caption_limit
        return PostingResult(
            platform_slug=request.platform_slug,
            status="validation_failed",
            attempted_at=attempted_at,
            error_message=(
                f"{request.platform_display_name} allows up to {limit} characters, "
                f"but this posting text is {text_metrics.character_count}."
            ),
        )

    return adapter.validate(
        request,
        settings,
        attempted_at=attempted_at,
    )


def _guard_against_duplicate_successes(
    session: Session,
    *,
    post_id: int,
    platform_slugs: tuple[str, ...],
) -> None:
    existing_platform_slugs = tuple(
        dict.fromkeys(
            session.scalars(
                select(PostPlatformLog.platform_slug).where(
                    PostPlatformLog.post_id == post_id,
                    PostPlatformLog.platform_slug.in_(platform_slugs),
                    PostPlatformLog.status == "posted",
                )
            ).all()
        )
    )
    if existing_platform_slugs:
        raise DuplicateSubmissionError(existing_platform_slugs)


def _apply_posting_result(log: PostPlatformLog, result: PostingResult) -> None:
    log.status = result.status
    log.posted_at = result.posted_at
    log.external_post_id = result.external_post_id
    log.error_message = result.error_message
    log.response_summary = result.response_summary


def _is_readable_file(path: Path) -> bool:
    try:
        with path.open("rb") as file_handle:
            file_handle.read(1)
        return True
    except OSError:
        return False


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _build_posting_connected_account(
    account: ConnectedAccount,
) -> PostingConnectedAccount:
    scopes = tuple(scope for scope in account.scopes.split(",") if scope)
    return PostingConnectedAccount(
        provider_slug=account.provider_slug,
        provider_account_id=account.provider_account_id,
        display_name=account.display_name,
        username=account.username,
        access_token=account.access_token or "",
        refresh_token=account.refresh_token,
        token_type=account.token_type,
        scopes=scopes,
    )
