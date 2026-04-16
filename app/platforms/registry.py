from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import Settings


@dataclass(frozen=True, slots=True)
class PlatformDefinition:
    slug: str
    display_name: str
    required_settings: tuple[str, ...]
    supports_carousel: bool
    max_carousel_items: int
    allowed_media_types: tuple[str, ...]
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
        caption_limit=2200,
        validation_notes="Phase 3 visibility is based on a local access token only.",
    ),
    PlatformDefinition(
        slug="facebook",
        display_name="Facebook",
        required_settings=("facebook_page_id",),
        supports_carousel=False,
        max_carousel_items=1,
        allowed_media_types=("image", "video"),
        validation_notes=(
            "Phase 3 uses page ID presence as a lightweight visibility check."
        ),
    ),
    PlatformDefinition(
        slug="x",
        display_name="X",
        required_settings=("x_api_key",),
        supports_carousel=True,
        max_carousel_items=4,
        allowed_media_types=("image", "video"),
        caption_limit=280,
        validation_notes="Phase 3 visibility is based on an API key placeholder only.",
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
