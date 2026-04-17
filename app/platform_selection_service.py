"""Platform selection workflow helpers for configured local platforms."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.accounts_service import list_provider_runtime_states
from app.config import Settings, get_settings
from app.db import Post
from app.platforms import PlatformDefinition


@dataclass(frozen=True, slots=True)
class WorkflowMediaItemSummary:
    """Minimal media item state shown during workflow selection and review."""

    display_order: int
    original_filename: str | None
    media_type: str
    width: int | None
    height: int | None
    file_path: str

    @property
    def label(self) -> str:
        return self.original_filename or Path(self.file_path).name


@dataclass(frozen=True, slots=True)
class WorkflowMasterPostSummary:
    """Master post details needed after compose succeeds."""

    id: int
    caption: str
    hashtags: str
    media_items: tuple[WorkflowMediaItemSummary, ...]

    @property
    def media_count(self) -> int:
        return len(self.media_items)


@dataclass(frozen=True, slots=True)
class PlatformChoice:
    """Rendered platform option for selection or review."""

    slug: str
    display_name: str
    supports_carousel: bool
    max_carousel_items: int
    allowed_media_types: tuple[str, ...]
    carousel_allowed_media_types: tuple[str, ...]
    caption_limit: int | None
    validation_notes: str
    selected: bool = False
    eligible: bool = True
    ineligibility_reason: str | None = None


@dataclass(frozen=True, slots=True)
class PlatformSelectionFormData:
    """Normalized selected-platform values from the server-rendered form."""

    selected_platform_slugs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PlatformSelectionState:
    """Selection page state for one saved master post."""

    post_summary: WorkflowMasterPostSummary
    eligible_platforms: tuple[PlatformChoice, ...]
    ineligible_platforms: tuple[PlatformChoice, ...]
    unavailable_platforms: tuple["PlatformAvailabilityNotice", ...] = ()

    @property
    def connected_platforms(self) -> tuple[PlatformChoice, ...]:
        return self.eligible_platforms + self.ineligible_platforms

    @property
    def has_connected_platforms(self) -> bool:
        return bool(self.connected_platforms)

    @property
    def has_eligible_platforms(self) -> bool:
        return bool(self.eligible_platforms)

    @property
    def has_connectable_platforms(self) -> bool:
        return bool(self.unavailable_platforms)


@dataclass(frozen=True, slots=True)
class PlatformAvailabilityNotice:
    slug: str
    display_name: str
    status: str
    message: str


@dataclass(slots=True)
class PlatformSelectionValidationResult:
    """Validated selection outcome returned to routes."""

    form: PlatformSelectionFormData
    field_errors: dict[str, list[str]] = field(default_factory=dict)
    non_field_errors: list[str] = field(default_factory=list)
    selected_platform_slugs: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return (
            bool(self.selected_platform_slugs)
            and not self.field_errors
            and not self.non_field_errors
        )


@dataclass(frozen=True, slots=True)
class PlatformReviewState:
    """Read-only handoff state rendered by the platform review page."""

    post_summary: WorkflowMasterPostSummary
    selected_platforms: tuple[PlatformChoice, ...]


def empty_platform_selection_form() -> PlatformSelectionFormData:
    return PlatformSelectionFormData()


def build_platform_selection_page_context(
    *,
    state: PlatformSelectionState | None = None,
    form: PlatformSelectionFormData | None = None,
    field_errors: dict[str, list[str]] | None = None,
    non_field_errors: list[str] | None = None,
) -> dict[str, object]:
    return {
        "platform_selection_state": state,
        "post_summary": state.post_summary if state is not None else None,
        "eligible_platforms": state.eligible_platforms if state is not None else (),
        "ineligible_platforms": (
            state.ineligible_platforms if state is not None else ()
        ),
        "unavailable_platforms": (
            state.unavailable_platforms if state is not None else ()
        ),
        "platform_selection_form": form or empty_platform_selection_form(),
        "field_errors": field_errors or {},
        "non_field_errors": non_field_errors or [],
    }


def build_platform_review_page_context(
    *,
    review_state: PlatformReviewState | None = None,
    review_errors: list[str] | None = None,
    platform_selection_url: str | None = None,
) -> dict[str, object]:
    return {
        "review_state": review_state,
        "review_post_summary": (
            review_state.post_summary if review_state is not None else None
        ),
        "selected_platforms": (
            review_state.selected_platforms if review_state is not None else ()
        ),
        "review_errors": review_errors or [],
        "platform_selection_url": platform_selection_url,
    }


def load_platform_selection_state(
    session: Session,
    *,
    post_id: int,
    selected_platform_slugs: Sequence[str] = (),
    settings: Settings | None = None,
) -> PlatformSelectionState | None:
    """Load one saved master post and derive configured platform choices."""

    post = session.scalar(
        select(Post).options(selectinload(Post.media_items)).where(Post.id == post_id)
    )
    if post is None:
        return None

    post_summary = WorkflowMasterPostSummary(
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
    selected_lookup = set(_clean_selected_platform_slugs(selected_platform_slugs))
    resolved_settings = settings or get_settings()

    eligible_platforms: list[PlatformChoice] = []
    ineligible_platforms: list[PlatformChoice] = []
    unavailable_platforms: list[PlatformAvailabilityNotice] = []
    for provider_state in list_provider_runtime_states(
        session,
        settings=resolved_settings,
    ):
        platform = provider_state.platform
        if not provider_state.connected:
            if provider_state.connectable:
                unavailable_platforms.append(
                    PlatformAvailabilityNotice(
                        slug=platform.slug,
                        display_name=platform.display_name,
                        status=provider_state.connection_status,
                        message=provider_state.connection_message,
                    )
                )
            continue

        ineligibility_reason = _get_ineligibility_reason(
            platform,
            post_summary,
        )
        choice = PlatformChoice(
            slug=platform.slug,
            display_name=platform.display_name,
            supports_carousel=platform.supports_carousel,
            max_carousel_items=platform.max_carousel_items,
            allowed_media_types=platform.allowed_media_types,
            carousel_allowed_media_types=platform.carousel_allowed_media_types,
            caption_limit=platform.caption_limit,
            validation_notes=platform.validation_notes,
            selected=platform.slug in selected_lookup,
            eligible=ineligibility_reason is None,
            ineligibility_reason=ineligibility_reason,
        )
        if choice.eligible:
            eligible_platforms.append(choice)
        else:
            ineligible_platforms.append(choice)

    return PlatformSelectionState(
        post_summary=post_summary,
        eligible_platforms=tuple(eligible_platforms),
        ineligible_platforms=tuple(ineligible_platforms),
        unavailable_platforms=tuple(unavailable_platforms),
    )


def validate_platform_selection(
    state: PlatformSelectionState,
    *,
    selected_platform_slugs: Sequence[str],
) -> PlatformSelectionValidationResult:
    """Validate user-selected platforms against configured eligible choices."""

    cleaned_slugs = _clean_selected_platform_slugs(selected_platform_slugs)
    duplicate_slugs = _find_duplicate_selected_platform_slugs(selected_platform_slugs)
    eligible_platform_lookup = {platform.slug for platform in state.eligible_platforms}
    connected_platform_lookup = {
        platform.slug for platform in state.connected_platforms
    }
    normalized_selected_slugs = tuple(
        platform.slug
        for platform in state.eligible_platforms
        if platform.slug in cleaned_slugs
    )
    form = PlatformSelectionFormData(
        selected_platform_slugs=normalized_selected_slugs,
    )
    field_errors: dict[str, list[str]] = {}

    if not cleaned_slugs:
        field_errors["platform_slug"] = [
            "Select at least one connected platform before continuing."
        ]
        return PlatformSelectionValidationResult(form=form, field_errors=field_errors)

    if duplicate_slugs:
        field_errors.setdefault("platform_slug", []).append(
            "Each platform can only be selected once."
        )

    if any(slug not in connected_platform_lookup for slug in cleaned_slugs):
        field_errors.setdefault("platform_slug", []).append(
            "Choose only connected platforms shown on this page."
        )

    if any(
        slug in connected_platform_lookup and slug not in eligible_platform_lookup
        for slug in cleaned_slugs
    ):
        field_errors.setdefault("platform_slug", []).append(
            "Remove platforms that are not eligible for this master post yet."
        )

    return PlatformSelectionValidationResult(
        form=form,
        field_errors=field_errors,
        selected_platform_slugs=normalized_selected_slugs if not field_errors else (),
    )


def build_platform_review_state(
    state: PlatformSelectionState,
    *,
    selected_platform_slugs: Sequence[str],
) -> PlatformReviewState:
    """Build the read-only review handoff from a validated selection."""

    selected_lookup = set(selected_platform_slugs)
    return PlatformReviewState(
        post_summary=state.post_summary,
        selected_platforms=tuple(
            platform
            for platform in state.eligible_platforms
            if platform.slug in selected_lookup
        ),
    )


def collect_selection_errors(
    result: PlatformSelectionValidationResult,
) -> list[str]:
    """Flatten validation errors into a display-ready list."""

    errors = list(result.non_field_errors)
    for field_error_list in result.field_errors.values():
        errors.extend(field_error_list)
    return errors


def _clean_selected_platform_slugs(values: Sequence[str]) -> tuple[str, ...]:
    cleaned_values: list[str] = []
    for value in values:
        cleaned_value = str(value).strip()
        if cleaned_value:
            cleaned_values.append(cleaned_value)
    return tuple(dict.fromkeys(cleaned_values))


def _find_duplicate_selected_platform_slugs(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        cleaned_value = str(value).strip()
        if not cleaned_value:
            continue
        if cleaned_value in seen:
            duplicates.append(cleaned_value)
            continue
        seen.add(cleaned_value)
    return tuple(dict.fromkeys(duplicates))


def _get_ineligibility_reason(
    platform: PlatformDefinition,
    post_summary: WorkflowMasterPostSummary,
) -> str | None:
    if not post_summary.media_items:
        return "This master post does not have any media items yet."

    if post_summary.media_count > 1 and not platform.supports_carousel:
        return (
            f"{platform.display_name} does not support multi-image carousel posts "
            "in this workflow."
        )

    allowed_media_types = (
        platform.carousel_allowed_media_types
        if post_summary.media_count > 1
        else platform.allowed_media_types
    )
    unsupported_media_types = sorted(
        {
            media_item.media_type
            for media_item in post_summary.media_items
            if media_item.media_type not in allowed_media_types
        }
    )
    if unsupported_media_types:
        unsupported_media_label = ", ".join(unsupported_media_types)
        if post_summary.media_count > 1:
            return (
                f"{platform.display_name} carousel posts are not ready for "
                f"{unsupported_media_label} media items in this workflow."
            )
        return (
            f"{platform.display_name} is not ready for {unsupported_media_label} "
            "media items in this workflow."
        )

    if post_summary.media_count > platform.max_carousel_items:
        if platform.max_carousel_items == 1:
            return (
                f"{platform.display_name} only supports a single media item in "
                "this workflow."
            )
        return (
            f"{platform.display_name} currently supports up to "
            f"{platform.max_carousel_items} media items in this workflow."
        )

    return None
