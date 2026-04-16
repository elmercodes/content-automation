from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.config import Settings
from app.platform_selection_service import (
    PlatformChoice,
    PlatformReviewState,
    WorkflowMasterPostSummary,
    WorkflowMediaItemSummary,
)
from app.platforms import get_platform
from app.preview_service import build_platform_review_page_state, build_posting_text


def build_test_settings(tmp_path: Path) -> Settings:
    storage_root = tmp_path / "storage"
    uploads_dir = storage_root / "uploads"
    generated_dir = storage_root / "generated"
    database_path = storage_root / "db" / "app.db"
    for path in (uploads_dir, generated_dir, database_path.parent):
        path.mkdir(parents=True, exist_ok=True)
    return Settings(
        _env_file=None,
        storage_root=storage_root,
        uploads_dir=uploads_dir,
        generated_dir=generated_dir,
        database_url=f"sqlite:///{database_path}",
    )


def create_media_item(
    settings: Settings,
    *,
    post_id: int,
    display_order: int,
    size: tuple[int, int] = (48, 36),
) -> WorkflowMediaItemSummary:
    relative_path = (
        Path("uploads") / "posts" / str(post_id) / f"{display_order:03d}-preview.png"
    )
    absolute_path = settings.storage_root_path / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(90, 60, 40)).save(absolute_path, format="PNG")
    return WorkflowMediaItemSummary(
        display_order=display_order,
        original_filename=f"preview-{display_order}.png",
        media_type="image",
        width=size[0],
        height=size[1],
        file_path=relative_path.as_posix(),
    )


def build_platform_choice(slug: str) -> PlatformChoice:
    platform = get_platform(slug)
    return PlatformChoice(
        slug=platform.slug,
        display_name=platform.display_name,
        supports_carousel=platform.supports_carousel,
        max_carousel_items=platform.max_carousel_items,
        allowed_media_types=platform.allowed_media_types,
        caption_limit=platform.caption_limit,
        validation_notes=platform.validation_notes,
    )


def test_build_posting_text_combines_caption_and_hashtags() -> None:
    assert (
        build_posting_text("Launch locally", "#phase7") == "Launch locally\n\n#phase7"
    )
    assert build_posting_text("Launch locally", "") == "Launch locally"
    assert build_posting_text("", "#phase7") == "#phase7"


def test_build_platform_review_page_state_flags_over_limit_for_x(
    tmp_path: Path,
) -> None:
    settings = build_test_settings(tmp_path)
    media_item = create_media_item(settings, post_id=4, display_order=0)
    review_state = PlatformReviewState(
        post_summary=WorkflowMasterPostSummary(
            id=4,
            caption="x" * 279,
            hashtags="#phase7",
            media_items=(media_item,),
        ),
        selected_platforms=(build_platform_choice("x"),),
    )

    page = build_platform_review_page_state(review_state, settings=settings)

    assert page.current_preview.preview_image is not None
    assert page.current_preview.text_metrics.over_limit is True
    assert {warning.code for warning in page.current_preview.warnings} == {"over_limit"}


def test_build_platform_review_page_state_marks_multi_image_preview_as_partial(
    tmp_path: Path,
) -> None:
    settings = build_test_settings(tmp_path)
    review_state = PlatformReviewState(
        post_summary=WorkflowMasterPostSummary(
            id=7,
            caption="Launch locally",
            hashtags="#phase7",
            media_items=(
                create_media_item(settings, post_id=7, display_order=0, size=(48, 36)),
                create_media_item(settings, post_id=7, display_order=1, size=(36, 48)),
            ),
        ),
        selected_platforms=(build_platform_choice("instagram"),),
    )

    page = build_platform_review_page_state(review_state, settings=settings)

    assert page.current_preview.primary_media_item is not None
    assert page.current_preview.primary_media_item.display_order == 0
    assert len(page.current_preview.additional_media_items) == 1
    assert "multi_image_preview_partial" in {
        warning.code for warning in page.current_preview.warnings
    }


def test_build_platform_review_page_state_reports_unknown_limit_for_facebook(
    tmp_path: Path,
) -> None:
    settings = build_test_settings(tmp_path)
    review_state = PlatformReviewState(
        post_summary=WorkflowMasterPostSummary(
            id=9,
            caption="Local launch",
            hashtags="#phase7",
            media_items=(create_media_item(settings, post_id=9, display_order=0),),
        ),
        selected_platforms=(build_platform_choice("facebook"),),
    )

    page = build_platform_review_page_state(review_state, settings=settings)

    assert page.current_preview.text_metrics.limit is None
    assert "limit_unknown" in {
        warning.code for warning in page.current_preview.warnings
    }
