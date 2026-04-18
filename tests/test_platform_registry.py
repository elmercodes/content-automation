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
        instagram_client_id="instagram-client",
        instagram_client_secret="instagram-secret",
        x_client_id="x-client",
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

    assert facebook.missing_settings(settings) == (
        "facebook_client_id",
        "facebook_client_secret",
    )
    assert facebook_context["missing_settings"] == (
        "facebook_client_id",
        "facebook_client_secret",
    )
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
    assert facebook.posting_spec.enabled is True
    assert facebook.posting_spec.required_scopes == ("pages_manage_posts",)
    assert x_platform.posting_spec.enabled is True
    assert x_platform.posting_spec.required_settings == ()
    assert x_platform.posting_spec.required_scopes == (
        "tweet.write",
        "media.write",
        "users.read",
    )


def test_x_can_be_visible_without_being_posting_ready() -> None:
    settings = Settings(_env_file=None, x_client_id="x-client")
    x_context = next(
        platform
        for platform in get_supported_platform_context(settings)
        if platform["slug"] == "x"
    )

    assert x_context["configured"] is True
    assert x_context["missing_settings"] == ()
    assert x_context["posting_spec"]["enabled"] is True
    assert x_context["posting_spec"]["missing_settings"] == ()
    assert x_context["posting_spec"]["required_scopes"] == (
        "tweet.write",
        "media.write",
        "users.read",
    )
