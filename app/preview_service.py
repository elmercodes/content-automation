"""Preview-state assembly for the Phase 7 server-rendered review step."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings
from app.image_normalization import (
    GeneratedPreviewFile,
    PreviewGenerationError,
    generate_platform_preview_file,
)
from app.platform_selection_service import (
    PlatformChoice,
    PlatformReviewState,
    WorkflowMediaItemSummary,
)
from app.platforms import PlatformPreviewSpec, get_platform


@dataclass(frozen=True, slots=True)
class PreviewWarning:
    code: str
    severity: str
    message: str


@dataclass(frozen=True, slots=True)
class PostingTextMetrics:
    caption: str
    hashtags: str
    posting_text: str
    character_count: int
    limit: int | None
    remaining_characters: int | None
    over_limit: bool


@dataclass(frozen=True, slots=True)
class CurrentPlatformPreviewState:
    platform: PlatformChoice
    preview_spec: PlatformPreviewSpec
    primary_media_item: WorkflowMediaItemSummary | None
    additional_media_items: tuple[WorkflowMediaItemSummary, ...]
    preview_image: GeneratedPreviewFile | None
    text_metrics: PostingTextMetrics
    warnings: tuple[PreviewWarning, ...]


@dataclass(frozen=True, slots=True)
class PlatformReviewPageState:
    post_id: int
    selected_platforms: tuple[PlatformChoice, ...]
    current_platform_index: int
    current_preview: CurrentPlatformPreviewState

    @property
    def total_platforms(self) -> int:
        return len(self.selected_platforms)


def build_posting_text(caption: str, hashtags: str) -> str:
    cleaned_caption = caption.strip()
    cleaned_hashtags = hashtags.strip()
    if cleaned_caption and cleaned_hashtags:
        return f"{cleaned_caption}\n\n{cleaned_hashtags}"
    return cleaned_caption or cleaned_hashtags


def build_posting_text_metrics(
    *,
    caption: str,
    hashtags: str,
    limit: int | None,
) -> PostingTextMetrics:
    posting_text = build_posting_text(caption, hashtags)
    character_count = len(posting_text)
    remaining_characters = None if limit is None else limit - character_count
    return PostingTextMetrics(
        caption=caption,
        hashtags=hashtags,
        posting_text=posting_text,
        character_count=character_count,
        limit=limit,
        remaining_characters=remaining_characters,
        over_limit=limit is not None and character_count > limit,
    )


def build_platform_review_page_state(
    review_state: PlatformReviewState,
    *,
    platform_index: int = 0,
    settings: Settings | None = None,
) -> PlatformReviewPageState:
    if not review_state.selected_platforms:
        raise ValueError("At least one selected platform is required for review.")

    resolved_settings = settings or get_settings()
    current_platform_index = _clamp_platform_index(
        platform_index,
        len(review_state.selected_platforms),
    )
    current_platform = review_state.selected_platforms[current_platform_index]
    current_preview = build_current_platform_preview(
        review_state,
        platform=current_platform,
        settings=resolved_settings,
    )
    return PlatformReviewPageState(
        post_id=review_state.post_summary.id,
        selected_platforms=review_state.selected_platforms,
        current_platform_index=current_platform_index,
        current_preview=current_preview,
    )


def build_current_platform_preview(
    review_state: PlatformReviewState,
    *,
    platform: PlatformChoice,
    settings: Settings | None = None,
) -> CurrentPlatformPreviewState:
    resolved_settings = settings or get_settings()
    platform_definition = get_platform(platform.slug)
    preview_spec = platform_definition.preview_spec
    post_summary = review_state.post_summary
    text_metrics = build_posting_text_metrics(
        caption=post_summary.caption,
        hashtags=post_summary.hashtags,
        limit=platform.caption_limit,
    )
    primary_media_item = (
        post_summary.media_items[0] if post_summary.media_items else None
    )
    additional_media_items = tuple(post_summary.media_items[1:])

    warnings: list[PreviewWarning] = []
    preview_image: GeneratedPreviewFile | None = None

    if text_metrics.limit is None:
        warnings.append(
            PreviewWarning(
                code="limit_unknown",
                severity="info",
                message=(
                    "No known character limit is stored in the platform registry for "
                    f"{platform.display_name} yet."
                ),
            )
        )
    elif text_metrics.over_limit:
        warnings.append(
            PreviewWarning(
                code="over_limit",
                severity="warning",
                message=(
                    f"The current posting text is {text_metrics.character_count} "
                    f"characters, which exceeds the {platform.display_name} limit of "
                    f"{text_metrics.limit}."
                ),
            )
        )

    if post_summary.media_count > 1:
        warnings.append(
            PreviewWarning(
                code="multi_image_preview_partial",
                severity="info",
                message=(
                    "Phase 7 previews only the first media item visually. Full "
                    "ordered carousel preview is deferred to Phase 8."
                ),
            )
        )

    if primary_media_item is None:
        warnings.append(
            PreviewWarning(
                code="preview_generation_failed",
                severity="error",
                message="This master post does not have any media items to preview.",
            )
        )
    elif primary_media_item.media_type != "image":
        warnings.append(
            PreviewWarning(
                code="preview_generation_failed",
                severity="error",
                message=(
                    "Preview generation currently supports image media items only."
                ),
            )
        )
    else:
        try:
            preview_image = generate_platform_preview_file(
                primary_media_item,
                post_id=post_summary.id,
                platform_slug=platform.slug,
                preview_spec=preview_spec,
                settings=resolved_settings,
            )
        except PreviewGenerationError as exc:
            warnings.append(
                PreviewWarning(
                    code="preview_generation_failed",
                    severity="error",
                    message=str(exc),
                )
            )

    return CurrentPlatformPreviewState(
        platform=platform,
        preview_spec=preview_spec,
        primary_media_item=primary_media_item,
        additional_media_items=additional_media_items,
        preview_image=preview_image,
        text_metrics=text_metrics,
        warnings=tuple(warnings),
    )


def _clamp_platform_index(platform_index: int, total_platforms: int) -> int:
    if total_platforms <= 1:
        return 0
    return max(0, min(platform_index, total_platforms - 1))
