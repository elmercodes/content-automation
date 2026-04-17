"""X posting adapter for local single-image and image-carousel submissions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable, Mapping
from urllib.parse import parse_qsl, quote, urlparse

import httpx

from app.config import Settings
from app.platforms.adapters import PostingRequest, PostingResult


class XAdapter:
    MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
    STATUS_UPDATE_URL = "https://api.twitter.com/1.1/statuses/update.json"

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
        posting_spec = request.platform_definition.posting_spec
        missing_settings = posting_spec.missing_settings(settings)
        if missing_settings:
            missing_label = ", ".join(missing_settings)
            return PostingResult(
                platform_slug=request.platform_slug,
                status="not_configured",
                attempted_at=attempted_at,
                error_message=(
                    f"X posting is missing required local settings: {missing_label}."
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

        try:
            with self._client_factory() as client:
                media_ids = [
                    self._upload_media(
                        client,
                        request=request,
                        media_item=media_item,
                        settings=settings,
                    )
                    for media_item in request.media_items
                ]
                payload = {"status": request.posting_text}
                if media_ids:
                    payload["media_ids"] = ",".join(media_ids)
                response = client.post(
                    self.STATUS_UPDATE_URL,
                    data=payload,
                    headers={
                        "Authorization": _build_oauth_header(
                            method="POST",
                            url=self.STATUS_UPDATE_URL,
                            settings=settings,
                            body_params=payload,
                        ),
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

        external_post_id = payload.get("id_str") or (
            str(payload.get("id")) if payload.get("id") is not None else None
        )
        if external_post_id is None:
            return PostingResult(
                platform_slug=request.platform_slug,
                status="submission_failed",
                attempted_at=attempted_at,
                error_message="X did not return a post identifier.",
                response_summary=_truncate_summary(json.dumps(payload, sort_keys=True)),
            )

        media_entities = payload.get("extended_entities", {}).get("media", [])
        media_ids = [
            entity.get("id_str") or str(entity.get("id"))
            for entity in media_entities
            if entity.get("id_str") or entity.get("id") is not None
        ]
        response_summary = json.dumps(
            {
                "tweet_id": external_post_id,
                "media_ids": media_ids,
            },
            sort_keys=True,
        )
        return PostingResult(
            platform_slug=request.platform_slug,
            status="posted",
            attempted_at=attempted_at,
            posted_at=attempted_at,
            external_post_id=external_post_id,
            response_summary=response_summary,
        )

    def _upload_media(
        self,
        client: httpx.Client,
        *,
        request: PostingRequest,
        media_item,
        settings: Settings,
    ) -> str:
        with media_item.absolute_path.open("rb") as file_handle:
            response = client.post(
                self.MEDIA_UPLOAD_URL,
                files={
                    "media": (
                        media_item.original_filename or media_item.absolute_path.name,
                        file_handle,
                        "application/octet-stream",
                    )
                },
                headers={
                    "Authorization": _build_oauth_header(
                        method="POST",
                        url=self.MEDIA_UPLOAD_URL,
                        settings=settings,
                    ),
                },
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise exc

        payload = response.json()
        media_id = payload.get("media_id_string") or (
            str(payload.get("media_id"))
            if payload.get("media_id") is not None
            else None
        )
        if media_id is None:
            raise httpx.HTTPError(
                f"X upload for {request.platform_display_name} returned no media ID."
            )
        return media_id

    @staticmethod
    def _build_client() -> httpx.Client:
        return httpx.Client(timeout=30.0)


def _build_oauth_header(
    *,
    method: str,
    url: str,
    settings: Settings,
    body_params: Mapping[str, str] | None = None,
) -> str:
    oauth_params = {
        "oauth_consumer_key": settings.x_api_key or "",
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": settings.x_access_token or "",
        "oauth_version": "1.0",
    }
    signature = _build_signature(
        method=method,
        url=url,
        oauth_params=oauth_params,
        body_params=body_params or {},
        consumer_secret=settings.x_api_secret or "",
        token_secret=settings.x_access_token_secret or "",
    )
    oauth_params["oauth_signature"] = signature
    return "OAuth " + ", ".join(
        f'{_percent_encode(key)}="{_percent_encode(value)}"'
        for key, value in sorted(oauth_params.items())
    )


def _build_signature(
    *,
    method: str,
    url: str,
    oauth_params: Mapping[str, str],
    body_params: Mapping[str, str],
    consumer_secret: str,
    token_secret: str,
) -> str:
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    query_items = parse_qsl(parsed_url.query, keep_blank_values=True)
    normalized_items = list(query_items)
    normalized_items.extend(oauth_params.items())
    normalized_items.extend(body_params.items())
    parameter_string = "&".join(
        f"{_percent_encode(key)}={_percent_encode(value)}"
        for key, value in sorted(
            (_percent_encode(str(key)), _percent_encode(str(value)))
            for key, value in normalized_items
        )
    )
    signature_base_string = "&".join(
        (
            method.upper(),
            _percent_encode(base_url),
            _percent_encode(parameter_string),
        )
    )
    signing_key = "&".join(
        (
            _percent_encode(consumer_secret),
            _percent_encode(token_secret),
        )
    )
    digest = hmac.new(
        signing_key.encode("utf-8"),
        signature_base_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def _summarize_error_response(response: httpx.Response) -> str | None:
    try:
        summary = response.json()
        return _truncate_summary(json.dumps(summary, sort_keys=True))
    except ValueError:
        text = response.text.strip()
        return _truncate_summary(text) if text else None


def _truncate_summary(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1]}…"


def _percent_encode(value: str) -> str:
    return quote(value, safe="~-._")
