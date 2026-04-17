"""X posting adapter for local single-image and image-carousel submissions."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx

from app.config import Settings
from app.platforms.adapters import PostingRequest, PostingResult


class XAdapter:
    MEDIA_UPLOAD_URL = "https://api.x.com/2/media/upload"
    CREATE_POST_URL = "https://api.x.com/2/tweets"

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
        if connected_account is None or not connected_account.access_token:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="not_connected",
                attempted_at=attempted_at,
                error_message="Connect an X account before attempting to post.",
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
                    "Reconnect X to grant the required scopes: "
                    f"{', '.join(missing_scopes)}."
                ),
            )

        if request.media_count < 1:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="validation_failed",
                attempted_at=attempted_at,
                error_message="X posting requires at least one image.",
            )

        if request.is_carousel and not posting_spec.supports_image_carousel:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="unsupported",
                attempted_at=attempted_at,
                error_message="X carousel posting is not available in this workflow.",
            )

        if request.media_count > posting_spec.max_image_items:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="validation_failed",
                attempted_at=attempted_at,
                error_message=(
                    f"X supports up to {posting_spec.max_image_items} image items "
                    "per post."
                ),
            )

        if any(media_item.media_type != "image" for media_item in request.media_items):
            return PostingResult(
                platform_slug=request.platform_slug,
                status="validation_failed",
                attempted_at=attempted_at,
                error_message="X posting currently supports image media items only.",
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

        try:
            with self._client_factory() as client:
                media_ids = [
                    self._upload_media(
                        client,
                        media_item=media_item,
                        access_token=connected_account.access_token,
                    )
                    for media_item in request.media_items
                ]
                payload = {"text": request.posting_text}
                if media_ids:
                    payload["media"] = {"media_ids": media_ids}
                response = client.post(
                    self.CREATE_POST_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {connected_account.access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message=f"X returned HTTP {exc.response.status_code}.",
                response_summary=_summarize_error_response(exc.response),
            )
        except httpx.HTTPError as exc:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message=f"X submission failed before completion: {exc}.",
            )

        try:
            payload = response.json()
        except ValueError:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message="X returned an unreadable response payload.",
            )

        data = payload.get("data") or {}
        external_post_id = data.get("id")
        if external_post_id is None:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message="X did not return a post identifier.",
                response_summary=_truncate_summary(json.dumps(payload, sort_keys=True)),
            )

        response_summary = json.dumps(
            {
                "tweet_id": str(external_post_id),
                "media_ids": media_ids,
            },
            sort_keys=True,
        )
        return PostingResult(
            platform_slug=request.platform_slug,
            status="posted",
            attempted_at=attempted_at,
            posted_at=attempted_at,
            external_post_id=str(external_post_id),
            response_summary=response_summary,
        )

    def _upload_media(
        self,
        client: httpx.Client,
        *,
        media_item,
        access_token: str,
    ) -> str:
        with media_item.absolute_path.open("rb") as file_handle:
            response = client.post(
                self.MEDIA_UPLOAD_URL,
                data={"media_category": "tweet_image", "media_type": "image/png"},
                files={
                    "media": (
                        media_item.original_filename or media_item.absolute_path.name,
                        file_handle,
                        "image/png",
                    )
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        media_id = data.get("id")
        if media_id is None:
            raise httpx.HTTPError("X upload returned no media ID.")
        return str(media_id)

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
