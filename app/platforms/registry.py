from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from typing import Any

from app.config import Settings


@dataclass(frozen=True, slots=True)
class PlatformPreviewSpec:
    canvas_width: int
    canvas_height: int
    frame_label: str
    background_hex: str = "#F6F2EA"

    @property
    def canvas_size(self) -> tuple[int, int]:
        return (self.canvas_width, self.canvas_height)

    @property
    def aspect_ratio_label(self) -> str:
        divisor = gcd(self.canvas_width, self.canvas_height)
        return f"{self.canvas_width // divisor}:{self.canvas_height // divisor}"


@dataclass(frozen=True, slots=True)
class PlatformDefinition:
    slug: str
    display_name: str
    required_settings: tuple[str, ...]
    supports_carousel: bool
    max_carousel_items: int
    allowed_media_types: tuple[str, ...]
    preview_spec: PlatformPreviewSpec
    caption_limit: int | None = None
    validation_notes: str = ""

    def missing_settings(self, settings: Settings) -> tuple[str, ...]:
        return tuple(
            setting_name
            for setting_name in self.required_settings
            if not getattr(settings, setting_name)
        )

    def is_configured(self, settings: Settings) -> bool:
        return not self.missing_settings(settings)


PLATFORM_REGISTRY: tuple[PlatformDefinition, ...] = (
    PlatformDefinition(
        slug="instagram",
        display_name="Instagram",
        required_settings=("instagram_access_token",),
        supports_carousel=True,
        max_carousel_items=10,
        allowed_media_types=("image", "video"),
        preview_spec=PlatformPreviewSpec(
            canvas_width=1080,
            canvas_height=1350,
            frame_label="4:5 feed preview",
        ),
        caption_limit=2200,
        validation_notes="Configured visibility is based on a local access token.",
    ),
    PlatformDefinition(
        slug="facebook",
        display_name="Facebook",
        required_settings=("facebook_page_id",),
        supports_carousel=False,
        max_carousel_items=1,
        allowed_media_types=("image", "video"),
        preview_spec=PlatformPreviewSpec(
            canvas_width=1200,
            canvas_height=1200,
            frame_label="Square feed preview",
        ),
        validation_notes=(
            "Configured visibility uses page ID presence as a lightweight check."
        ),
    ),
    PlatformDefinition(
        slug="x",
        display_name="X",
        required_settings=("x_api_key",),
        supports_carousel=True,
        max_carousel_items=4,
        allowed_media_types=("image", "video"),
        preview_spec=PlatformPreviewSpec(
            canvas_width=1600,
            canvas_height=900,
            frame_label="Wide timeline preview",
        ),
        caption_limit=280,
        validation_notes="Configured visibility is based on a local API key.",
    ),
)

_PLATFORM_INDEX = {platform.slug: platform for platform in PLATFORM_REGISTRY}


def get_supported_platforms() -> tuple[PlatformDefinition, ...]:
    return PLATFORM_REGISTRY


def get_platform(slug: str) -> PlatformDefinition:
    try:
        return _PLATFORM_INDEX[slug]
    except KeyError as exc:
        raise KeyError(f"Unsupported platform: {slug}") from exc


def get_configured_platforms(settings: Settings) -> tuple[PlatformDefinition, ...]:
    return tuple(
        platform for platform in PLATFORM_REGISTRY if platform.is_configured(settings)
    )


def serialize_platform(
    platform: PlatformDefinition,
    settings: Settings,
) -> dict[str, Any]:
    missing_settings = platform.missing_settings(settings)
    return {
        "slug": platform.slug,
        "display_name": platform.display_name,
        "required_settings": platform.required_settings,
        "missing_settings": missing_settings,
        "configured": not missing_settings,
        "supports_carousel": platform.supports_carousel,
        "max_carousel_items": platform.max_carousel_items,
        "allowed_media_types": platform.allowed_media_types,
        "preview_spec": {
            "canvas_width": platform.preview_spec.canvas_width,
            "canvas_height": platform.preview_spec.canvas_height,
            "frame_label": platform.preview_spec.frame_label,
            "background_hex": platform.preview_spec.background_hex,
            "aspect_ratio_label": platform.preview_spec.aspect_ratio_label,
        },
        "caption_limit": platform.caption_limit,
        "validation_notes": platform.validation_notes,
    }


def get_supported_platform_context(settings: Settings) -> tuple[dict[str, Any], ...]:
    return tuple(
        serialize_platform(platform, settings) for platform in get_supported_platforms()
    )


def get_configured_platform_context(settings: Settings) -> tuple[dict[str, Any], ...]:
    return tuple(
        serialize_platform(platform, settings)
        for platform in get_configured_platforms(settings)
    )
