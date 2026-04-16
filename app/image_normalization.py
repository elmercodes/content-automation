"""Deterministic image normalization for generated platform previews."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor, ImageOps, UnidentifiedImageError

from app.config import Settings, get_settings
from app.platform_selection_service import WorkflowMediaItemSummary
from app.platforms import PlatformPreviewSpec

PREVIEW_VERSION = "v1"


class PreviewGenerationError(ValueError):
    """Raised when a generated preview file cannot be produced."""


@dataclass(frozen=True, slots=True)
class GeneratedPreviewFile:
    """Metadata for one generated preview artifact on local disk."""

    absolute_path: Path
    relative_path: str
    canvas_width: int
    canvas_height: int


def generate_platform_preview_file(
    media_item: WorkflowMediaItemSummary,
    *,
    post_id: int,
    platform_slug: str,
    preview_spec: PlatformPreviewSpec,
    settings: Settings | None = None,
) -> GeneratedPreviewFile:
    resolved_settings = settings or get_settings()
    if media_item.media_type != "image":
        raise PreviewGenerationError(
            "Preview generation currently supports image media items only."
        )

    source_path = resolved_settings.storage_root_path / media_item.file_path
    if not source_path.is_file():
        raise PreviewGenerationError(
            f"Preview source file is missing for {media_item.label}."
        )

    relative_path = build_preview_relative_path(
        post_id=post_id,
        platform_slug=platform_slug,
        display_order=media_item.display_order,
    )
    destination_path = resolved_settings.generated_path / relative_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    if _can_reuse_preview(destination_path, source_path):
        return GeneratedPreviewFile(
            absolute_path=destination_path,
            relative_path=relative_path.as_posix(),
            canvas_width=preview_spec.canvas_width,
            canvas_height=preview_spec.canvas_height,
        )

    try:
        with Image.open(source_path) as source_image:
            normalized_image = ImageOps.exif_transpose(source_image)
            normalized_image.load()
            rendered_image = _render_contained_preview(
                normalized_image=normalized_image,
                preview_spec=preview_spec,
            )
    except (UnidentifiedImageError, OSError) as exc:
        raise PreviewGenerationError(
            f"Preview generation failed because {media_item.label} is not readable."
        ) from exc

    try:
        rendered_image.save(destination_path, format="PNG")
    except OSError as exc:
        destination_path.unlink(missing_ok=True)
        raise PreviewGenerationError(
            f"Preview generation failed while saving {media_item.label}."
        ) from exc

    return GeneratedPreviewFile(
        absolute_path=destination_path,
        relative_path=relative_path.as_posix(),
        canvas_width=preview_spec.canvas_width,
        canvas_height=preview_spec.canvas_height,
    )


def build_preview_relative_path(
    *,
    post_id: int,
    platform_slug: str,
    display_order: int,
) -> Path:
    return (
        Path("previews")
        / PREVIEW_VERSION
        / "posts"
        / str(post_id)
        / platform_slug
        / (f"media-{display_order:03d}.png")
    )


def _can_reuse_preview(destination_path: Path, source_path: Path) -> bool:
    if not destination_path.is_file():
        return False
    return destination_path.stat().st_mtime_ns >= source_path.stat().st_mtime_ns


def _render_contained_preview(
    *,
    normalized_image: Image.Image,
    preview_spec: PlatformPreviewSpec,
) -> Image.Image:
    preview_canvas = Image.new(
        "RGBA",
        preview_spec.canvas_size,
        ImageColor.getrgb(preview_spec.background_hex) + (255,),
    )
    contained_image = ImageOps.contain(
        normalized_image.convert("RGBA"),
        preview_spec.canvas_size,
        method=Image.Resampling.LANCZOS,
    )
    offset_x = (preview_spec.canvas_width - contained_image.width) // 2
    offset_y = (preview_spec.canvas_height - contained_image.height) // 2
    preview_canvas.paste(contained_image, (offset_x, offset_y), contained_image)
    return preview_canvas.convert("RGB")
