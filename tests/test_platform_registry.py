import pytest

from app.config import Settings
from app.platforms import (
    get_configured_platform_context,
    get_configured_platforms,
    get_platform,
    get_supported_platform_context,
)


def test_platform_registry_only_marks_present_credentials_as_configured() -> None:
    settings = Settings(
        _env_file=None,
        instagram_access_token="local-token",
        x_api_key="local-key",
    )

    configured = get_configured_platforms(settings)
    supported_context = get_configured_platform_context(settings)

    assert [platform.slug for platform in configured] == ["instagram", "x"]
    assert [platform["slug"] for platform in supported_context] == ["instagram", "x"]


def test_platform_registry_reports_missing_required_settings() -> None:
    settings = Settings(_env_file=None)
    facebook = get_platform("facebook")
    facebook_context = next(
        platform
        for platform in get_supported_platform_context(settings)
        if platform["slug"] == "facebook"
    )

    assert facebook.missing_settings(settings) == ("facebook_page_id",)
    assert facebook_context["missing_settings"] == ("facebook_page_id",)
    assert facebook_context["configured"] is False


def test_unknown_platform_lookup_fails() -> None:
    with pytest.raises(KeyError, match="Unsupported platform"):
        get_platform("linkedin")


def test_platform_registry_exposes_image_only_carousel_rules_for_current_workflow() -> (
    None
):
    instagram = get_platform("instagram")
    facebook = get_platform("facebook")
    x_platform = get_platform("x")

    assert instagram.allowed_media_types == ("image",)
    assert instagram.carousel_allowed_media_types == ("image",)
    assert facebook.allowed_media_types == ("image",)
    assert facebook.carousel_allowed_media_types == ()
    assert instagram.posting_spec.enabled is False
    assert x_platform.posting_spec.enabled is True
    assert x_platform.posting_spec.required_settings == (
        "x_api_key",
        "x_api_secret",
        "x_access_token",
        "x_access_token_secret",
    )


def test_x_can_be_visible_without_being_posting_ready() -> None:
    settings = Settings(_env_file=None, x_api_key="local-key")
    x_context = next(
        platform
        for platform in get_supported_platform_context(settings)
        if platform["slug"] == "x"
    )

    assert x_context["configured"] is True
    assert x_context["missing_settings"] == ()
    assert x_context["posting_spec"]["enabled"] is True
    assert x_context["posting_spec"]["missing_settings"] == (
        "x_api_secret",
        "x_access_token",
        "x_access_token_secret",
    )
