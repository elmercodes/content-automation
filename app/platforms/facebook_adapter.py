"""Facebook Page photo posting adapter for the local single-image workflow."""

from __future__ import annotations

import json
import mimetypes
from collections.abc import Callable

import httpx

from app.config import Settings
from app.platforms.adapters import PostingRequest, PostingResult


class FacebookAdapter:
    def __init__(
        self,
        *,
        client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self._client_factory = client_factory or self._build_client

    def validate(
        self,
        request: PostingRequest,
        settings: Settings,
        *,
        attempted_at,
    ) -> PostingResult | None:
        del settings
        posting_spec = request.platform_definition.posting_spec
        connected_account = request.connected_account
        if (
            connected_account is None
            or not connected_account.access_token
            or not connected_account.provider_account_id
        ):
            return PostingResult(
                platform_slug=request.platform_slug,
                status="not_connected",
                attempted_at=attempted_at,
                error_message=("Connect a Facebook Page before attempting to post."),
            )

        missing_scopes = sorted(
            set(posting_spec.required_scopes) - set(connected_account.scopes)
        )
        if missing_scopes:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="reauthorization_required",
                attempted_at=attempted_at,
                error_message=(
                    "Reconnect Facebook to grant the required scopes: "
                    f"{', '.join(missing_scopes)}."
                ),
            )

        if request.media_count < 1:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="validation_failed",
                attempted_at=attempted_at,
                error_message="Facebook posting requires one image.",
            )

        if request.is_carousel or request.media_count > posting_spec.max_image_items:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="validation_failed",
                attempted_at=attempted_at,
                error_message="Facebook posting currently supports one image only.",
            )

        return None

    def submit(
        self,
        request: PostingRequest,
        settings: Settings,
        *,
        attempted_at,
    ) -> PostingResult:
        validation_result = self.validate(
            request,
            settings,
            attempted_at=attempted_at,
        )
        if validation_result is not None:
            return validation_result

        connected_account = request.connected_account
        assert connected_account is not None
        media_item = request.media_items[0]
        endpoint = (
            "https://graph.facebook.com/"
            f"{settings.meta_api_version}/{connected_account.provider_account_id}/photos"
        )
        content_type = (
            mimetypes.guess_type(media_item.absolute_path.name)[0]
            or "application/octet-stream"
        )
        data = {"published": "true"}
        if request.posting_text.strip():
            data["message"] = request.posting_text

        try:
            with self._client_factory() as client:
                with media_item.absolute_path.open("rb") as file_handle:
                    response = client.post(
                        endpoint,
                        data=data,
                        files={
                            "source": (
                                media_item.original_filename
                                or media_item.absolute_path.name,
                                file_handle,
                                content_type,
                            )
                        },
                        headers={
                            "Authorization": f"Bearer {connected_account.access_token}",
                        },
                    )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message=f"Facebook returned HTTP {exc.response.status_code}.",
                response_summary=_summarize_error_response(exc.response),
            )
        except httpx.HTTPError as exc:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message=f"Facebook submission failed before completion: {exc}.",
            )

        try:
            payload = response.json()
        except ValueError:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message="Facebook returned an unreadable response payload.",
            )

        external_post_id = payload.get("post_id") or payload.get("id")
        if external_post_id is None:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message="Facebook did not return a post identifier.",
                response_summary=_truncate_summary(json.dumps(payload, sort_keys=True)),
            )

        return PostingResult(
            platform_slug=request.platform_slug,
            status="posted",
            attempted_at=attempted_at,
            posted_at=attempted_at,
            external_post_id=str(external_post_id),
            response_summary=_truncate_summary(json.dumps(payload, sort_keys=True)),
        )

    @staticmethod
    def _build_client() -> httpx.Client:
        return httpx.Client(timeout=30.0)


def _summarize_error_response(response: httpx.Response) -> str | None:
    try:
        summary = response.json()
        return _truncate_summary(json.dumps(summary, sort_keys=True))
    except ValueError:
        text = response.text.strip()
        return _truncate_summary(text) if text else None


def _truncate_summary(value: str, *, limit: int = 500) -> str:
    trimmed = value.strip()
    if len(trimmed) <= limit:
        return trimmed
    return f"{trimmed[: limit - 1]}…"
