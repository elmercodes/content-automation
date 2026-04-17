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
class PlatformPostingSpec:
    enabled: bool
    supports_single_image: bool
    supports_image_carousel: bool
    max_image_items: int
    required_settings: tuple[str, ...] = ()
    required_scopes: tuple[str, ...] = ()
    notes: str = ""

    def missing_settings(self, settings: Settings) -> tuple[str, ...]:
        return tuple(
            setting_name
            for setting_name in self.required_settings
            if not getattr(settings, setting_name)
        )


@dataclass(frozen=True, slots=True)
class PlatformDefinition:
    slug: str
    display_name: str
    required_settings: tuple[str, ...]
    oauth_scopes: tuple[str, ...]
    supports_carousel: bool
    max_carousel_items: int
    allowed_media_types: tuple[str, ...]
    carousel_allowed_media_types: tuple[str, ...]
    preview_spec: PlatformPreviewSpec
    posting_spec: PlatformPostingSpec
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
        required_settings=("instagram_client_id", "instagram_client_secret"),
        oauth_scopes=("instagram_business_basic",),
        supports_carousel=True,
        max_carousel_items=10,
        allowed_media_types=("image",),
        carousel_allowed_media_types=("image",),
        preview_spec=PlatformPreviewSpec(
            canvas_width=1080,
            canvas_height=1350,
            frame_label="4:5 feed preview",
        ),
        posting_spec=PlatformPostingSpec(
            enabled=False,
            supports_single_image=False,
            supports_image_carousel=False,
            max_image_items=0,
            notes=(
                "Direct posting remains deferred because Meta content publishing "
                "requires media to be hosted on a public server at publish time."
            ),
        ),
        caption_limit=2200,
        validation_notes=(
            "Requires an Instagram professional account connected through the "
            "official Instagram login flow."
        ),
    ),
    PlatformDefinition(
        slug="facebook",
        display_name="Facebook",
        required_settings=("facebook_client_id", "facebook_client_secret"),
        oauth_scopes=("pages_show_list",),
        supports_carousel=False,
        max_carousel_items=1,
        allowed_media_types=("image",),
        carousel_allowed_media_types=(),
        preview_spec=PlatformPreviewSpec(
            canvas_width=1200,
            canvas_height=1200,
            frame_label="Square feed preview",
        ),
        posting_spec=PlatformPostingSpec(
            enabled=False,
            supports_single_image=False,
            supports_image_carousel=False,
            max_image_items=0,
            notes="Direct Facebook posting is deferred in the current workflow.",
        ),
        validation_notes=(
            "Requires a Facebook login plus local selection of a managed Page."
        ),
    ),
    PlatformDefinition(
        slug="x",
        display_name="X",
        required_settings=("x_client_id",),
        oauth_scopes=("tweet.write", "media.write", "users.read", "offline.access"),
        supports_carousel=True,
        max_carousel_items=4,
        allowed_media_types=("image",),
        carousel_allowed_media_types=("image",),
        preview_spec=PlatformPreviewSpec(
            canvas_width=1600,
            canvas_height=900,
            frame_label="Wide timeline preview",
        ),
        posting_spec=PlatformPostingSpec(
            enabled=True,
            supports_single_image=True,
            supports_image_carousel=True,
            max_image_items=4,
            required_scopes=("tweet.write", "media.write", "users.read"),
            notes=(
                "Posting uses stored OAuth 2.0 user tokens from a connected X "
                "account."
            ),
        ),
        caption_limit=280,
        validation_notes=(
            "Requires an X account connected through OAuth 2.0 with PKCE."
        ),
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
        "oauth_scopes": platform.oauth_scopes,
        "max_carousel_items": platform.max_carousel_items,
        "allowed_media_types": platform.allowed_media_types,
        "carousel_allowed_media_types": platform.carousel_allowed_media_types,
        "preview_spec": {
            "canvas_width": platform.preview_spec.canvas_width,
            "canvas_height": platform.preview_spec.canvas_height,
            "frame_label": platform.preview_spec.frame_label,
            "background_hex": platform.preview_spec.background_hex,
            "aspect_ratio_label": platform.preview_spec.aspect_ratio_label,
        },
        "posting_spec": {
            "enabled": platform.posting_spec.enabled,
            "supports_single_image": platform.posting_spec.supports_single_image,
            "supports_image_carousel": (platform.posting_spec.supports_image_carousel),
            "max_image_items": platform.posting_spec.max_image_items,
            "required_settings": platform.posting_spec.required_settings,
            "required_scopes": platform.posting_spec.required_scopes,
            "missing_settings": platform.posting_spec.missing_settings(settings),
            "notes": platform.posting_spec.notes,
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
