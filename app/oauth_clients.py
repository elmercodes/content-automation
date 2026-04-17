"""Provider-specific OAuth helpers for local connected-account flows."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.db import ConnectedAccount
from app.platforms import get_platform


class OAuthProviderError(ValueError):
    """Raised when a provider OAuth flow cannot be completed."""


@dataclass(frozen=True, slots=True)
class OAuthConnectedAccountPayload:
    provider_slug: str
    provider_account_id: str | None
    account_type: str | None
    display_name: str | None
    username: str | None
    access_token: str
    refresh_token: str | None
    token_type: str | None
    scopes: tuple[str, ...]
    expires_at: datetime | None
    refresh_expires_at: datetime | None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FacebookUserAuthorization:
    access_token: str
    token_type: str | None
    scopes: tuple[str, ...]
    expires_at: datetime | None
    user_id: str | None
    user_name: str | None


@dataclass(frozen=True, slots=True)
class FacebookPageOption:
    page_id: str
    page_name: str
    page_access_token: str
    instagram_business_account_id: str | None = None


class OAuthClient(Protocol):
    provider_slug: str
    supports_pkce: bool
    supports_refresh: bool

    def build_authorization_url(
        self,
        *,
        settings: Settings,
        callback_url: str,
        state_token: str,
        code_verifier: str | None = None,
    ) -> str: ...

    def exchange_code(
        self,
        *,
        settings: Settings,
        callback_url: str,
        code: str,
        code_verifier: str | None = None,
    ) -> OAuthConnectedAccountPayload | FacebookUserAuthorization: ...

    def refresh_connected_account(
        self,
        *,
        settings: Settings,
        account: ConnectedAccount,
    ) -> OAuthConnectedAccountPayload | None: ...


class BaseOAuthClient:
    provider_slug = ""
    supports_pkce = False
    supports_refresh = False

    def _build_client(self) -> httpx.Client:
        return httpx.Client(timeout=30.0)

    def refresh_connected_account(
        self,
        *,
        settings: Settings,
        account: ConnectedAccount,
    ) -> OAuthConnectedAccountPayload | None:
        del settings, account
        return None


class XOAuthClient(BaseOAuthClient):
    provider_slug = "x"
    supports_pkce = True
    supports_refresh = True
    AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
    TOKEN_URL = "https://api.x.com/2/oauth2/token"
    USER_URL = "https://api.x.com/2/users/me"

    def build_authorization_url(
        self,
        *,
        settings: Settings,
        callback_url: str,
        state_token: str,
        code_verifier: str | None = None,
    ) -> str:
        client_id = settings.x_client_id
        if not client_id:
            raise OAuthProviderError("X OAuth is missing app-level provider settings.")
        if not code_verifier:
            raise OAuthProviderError("X OAuth requires PKCE state.")

        query = urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": callback_url,
                "scope": " ".join(get_platform("x").oauth_scopes),
                "state": state_token,
                "code_challenge": build_pkce_code_challenge(code_verifier),
                "code_challenge_method": "S256",
            }
        )
        return f"{self.AUTHORIZE_URL}?{query}"

    def exchange_code(
        self,
        *,
        settings: Settings,
        callback_url: str,
        code: str,
        code_verifier: str | None = None,
    ) -> OAuthConnectedAccountPayload:
        client_id = settings.x_client_id
        if not client_id:
            raise OAuthProviderError("X OAuth is missing app-level provider settings.")
        if not code_verifier:
            raise OAuthProviderError("X OAuth requires PKCE state.")

        with self._build_client() as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_url,
                },
            )
            token_payload = _parse_json_response(response, provider_label="X")
            access_token = _require_token(token_payload, provider_label="X")
            profile_response = client.get(
                self.USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_payload = _parse_json_response(profile_response, provider_label="X")

        profile = profile_payload.get("data") or {}
        return OAuthConnectedAccountPayload(
            provider_slug="x",
            provider_account_id=_optional_str(profile.get("id")),
            account_type="x_user",
            display_name=_optional_str(profile.get("name")),
            username=_optional_str(profile.get("username")),
            access_token=access_token,
            refresh_token=_optional_str(token_payload.get("refresh_token")),
            token_type=_optional_str(token_payload.get("token_type")) or "Bearer",
            scopes=_normalize_scopes(token_payload.get("scope"))
            or get_platform("x").oauth_scopes,
            expires_at=_build_expiry_datetime(token_payload.get("expires_in")),
            refresh_expires_at=None,
            provider_metadata={"profile": profile},
        )

    def refresh_connected_account(
        self,
        *,
        settings: Settings,
        account: ConnectedAccount,
    ) -> OAuthConnectedAccountPayload:
        client_id = settings.x_client_id
        refresh_token = account.refresh_token
        if not client_id or not refresh_token:
            raise OAuthProviderError(
                "X refresh requires a client ID and refresh token."
            )

        with self._build_client() as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            token_payload = _parse_json_response(response, provider_label="X")
            access_token = _require_token(token_payload, provider_label="X")

        return OAuthConnectedAccountPayload(
            provider_slug="x",
            provider_account_id=account.provider_account_id,
            account_type=account.account_type,
            display_name=account.display_name,
            username=account.username,
            access_token=access_token,
            refresh_token=(
                _optional_str(token_payload.get("refresh_token")) or refresh_token
            ),
            token_type=_optional_str(token_payload.get("token_type")) or "Bearer",
            scopes=_normalize_scopes(token_payload.get("scope"))
            or _split_scopes(account.scopes),
            expires_at=_build_expiry_datetime(token_payload.get("expires_in")),
            refresh_expires_at=None,
            provider_metadata=_load_json_value(account.provider_metadata_json),
        )


class InstagramOAuthClient(BaseOAuthClient):
    provider_slug = "instagram"
    AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
    TOKEN_URL = "https://api.instagram.com/oauth/access_token"
    PROFILE_URL = (
        "https://graph.instagram.com/me"
        "?fields=user_id,username,name,profile_picture_url,account_type"
    )

    def build_authorization_url(
        self,
        *,
        settings: Settings,
        callback_url: str,
        state_token: str,
        code_verifier: str | None = None,
    ) -> str:
        del code_verifier
        client_id = settings.instagram_client_id
        if not client_id:
            raise OAuthProviderError(
                "Instagram OAuth is missing app-level provider settings."
            )

        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": callback_url,
                "response_type": "code",
                "scope": ",".join(get_platform("instagram").oauth_scopes),
                "state": state_token,
            }
        )
        return f"{self.AUTHORIZE_URL}?{query}"

    def exchange_code(
        self,
        *,
        settings: Settings,
        callback_url: str,
        code: str,
        code_verifier: str | None = None,
    ) -> OAuthConnectedAccountPayload:
        del code_verifier
        client_id = settings.instagram_client_id
        client_secret = settings.instagram_client_secret
        if not client_id or not client_secret:
            raise OAuthProviderError(
                "Instagram OAuth is missing app-level provider settings."
            )

        with self._build_client() as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_url,
                    "code": code,
                },
            )
            token_payload = _parse_json_response(
                response,
                provider_label="Instagram",
            )
            access_token = _require_token(token_payload, provider_label="Instagram")
            profile_response = client.get(
                self.PROFILE_URL,
                params={"access_token": access_token},
            )
            profile_payload = _parse_json_response(
                profile_response,
                provider_label="Instagram",
            )

        provider_account_id = _optional_str(
            profile_payload.get("user_id") or profile_payload.get("id")
        )
        return OAuthConnectedAccountPayload(
            provider_slug="instagram",
            provider_account_id=provider_account_id,
            account_type=_optional_str(profile_payload.get("account_type"))
            or "instagram_professional",
            display_name=_optional_str(profile_payload.get("name")),
            username=_optional_str(profile_payload.get("username")),
            access_token=access_token,
            refresh_token=_optional_str(token_payload.get("refresh_token")),
            token_type=_optional_str(token_payload.get("token_type")) or "Bearer",
            scopes=_normalize_scopes(token_payload.get("scope"))
            or get_platform("instagram").oauth_scopes,
            expires_at=_build_expiry_datetime(token_payload.get("expires_in")),
            refresh_expires_at=_build_expiry_datetime(
                token_payload.get("refresh_expires_in")
            ),
            provider_metadata={"profile": profile_payload},
        )


class FacebookOAuthClient(BaseOAuthClient):
    provider_slug = "facebook"

    def build_authorization_url(
        self,
        *,
        settings: Settings,
        callback_url: str,
        state_token: str,
        code_verifier: str | None = None,
    ) -> str:
        del code_verifier
        client_id = settings.facebook_client_id
        if not client_id:
            raise OAuthProviderError(
                "Facebook OAuth is missing app-level provider settings."
            )

        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": callback_url,
                "response_type": "code",
                "scope": ",".join(get_platform("facebook").oauth_scopes),
                "state": state_token,
            }
        )
        base_url = self._graph_url(
            settings,
            "dialog/oauth",
            host="www.facebook.com",
        )
        return f"{base_url}?{query}"

    def exchange_code(
        self,
        *,
        settings: Settings,
        callback_url: str,
        code: str,
        code_verifier: str | None = None,
    ) -> FacebookUserAuthorization:
        del code_verifier
        client_id = settings.facebook_client_id
        client_secret = settings.facebook_client_secret
        if not client_id or not client_secret:
            raise OAuthProviderError(
                "Facebook OAuth is missing app-level provider settings."
            )

        token_url = self._graph_url(settings, "oauth/access_token")
        with self._build_client() as client:
            response = client.get(
                token_url,
                params={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": callback_url,
                    "code": code,
                },
            )
            token_payload = _parse_json_response(response, provider_label="Facebook")
            access_token = _require_token(token_payload, provider_label="Facebook")

            profile_response = client.get(
                self._graph_url(settings, "me"),
                params={
                    "fields": "id,name",
                    "access_token": access_token,
                },
            )
            profile_payload = _parse_json_response(
                profile_response,
                provider_label="Facebook",
            )

        return FacebookUserAuthorization(
            access_token=access_token,
            token_type=_optional_str(token_payload.get("token_type")) or "Bearer",
            scopes=_normalize_scopes(token_payload.get("scope"))
            or get_platform("facebook").oauth_scopes,
            expires_at=_build_expiry_datetime(token_payload.get("expires_in")),
            user_id=_optional_str(profile_payload.get("id")),
            user_name=_optional_str(profile_payload.get("name")),
        )

    def load_page_options(
        self,
        *,
        settings: Settings,
        authorization: FacebookUserAuthorization,
    ) -> tuple[FacebookPageOption, ...]:
        with self._build_client() as client:
            response = client.get(
                self._graph_url(settings, "me/accounts"),
                params={
                    "fields": "id,name,access_token,instagram_business_account",
                    "access_token": authorization.access_token,
                },
            )
            payload = _parse_json_response(response, provider_label="Facebook")

        pages = payload.get("data") or ()
        options: list[FacebookPageOption] = []
        for page in pages:
            page_access_token = _optional_str(page.get("access_token"))
            page_id = _optional_str(page.get("id"))
            page_name = _optional_str(page.get("name"))
            if not page_access_token or not page_id or not page_name:
                continue
            instagram_business_account = page.get("instagram_business_account") or {}
            options.append(
                FacebookPageOption(
                    page_id=page_id,
                    page_name=page_name,
                    page_access_token=page_access_token,
                    instagram_business_account_id=_optional_str(
                        instagram_business_account.get("id")
                    ),
                )
            )
        return tuple(options)

    def _graph_url(
        self,
        settings: Settings,
        path: str,
        *,
        host: str | None = None,
    ) -> str:
        resolved_host = host or "graph.facebook.com"
        return f"https://{resolved_host}/{settings.meta_api_version}/{path.lstrip('/')}"


_CLIENTS: dict[str, OAuthClient] = {
    "facebook": FacebookOAuthClient(),
    "instagram": InstagramOAuthClient(),
    "x": XOAuthClient(),
}


def build_provider_callback_url(settings: Settings, provider_slug: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}/oauth/callback/{provider_slug}"


def build_pkce_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def get_oauth_client(provider_slug: str) -> OAuthClient:
    try:
        return _CLIENTS[provider_slug]
    except KeyError as exc:
        raise OAuthProviderError(
            f"Unsupported OAuth provider: {provider_slug}"
        ) from exc


def serialize_facebook_pending_payload(
    *,
    authorization: FacebookUserAuthorization,
    page_options: tuple[FacebookPageOption, ...],
) -> str:
    return json.dumps(
        {
            "authorization": {
                "access_token": authorization.access_token,
                "token_type": authorization.token_type,
                "scopes": list(authorization.scopes),
                "expires_at": _serialize_datetime(authorization.expires_at),
                "user_id": authorization.user_id,
                "user_name": authorization.user_name,
            },
            "page_options": [
                {
                    "page_id": option.page_id,
                    "page_name": option.page_name,
                    "page_access_token": option.page_access_token,
                    "instagram_business_account_id": (
                        option.instagram_business_account_id
                    ),
                }
                for option in page_options
            ],
        },
        sort_keys=True,
    )


def deserialize_facebook_pending_payload(
    payload_json: str | None,
) -> tuple[FacebookUserAuthorization, tuple[FacebookPageOption, ...]]:
    payload = _load_json_value(payload_json)
    authorization_payload = payload.get("authorization") or {}
    options_payload = payload.get("page_options") or ()
    authorization = FacebookUserAuthorization(
        access_token=_optional_str(authorization_payload.get("access_token")) or "",
        token_type=_optional_str(authorization_payload.get("token_type")),
        scopes=tuple(authorization_payload.get("scopes") or ()),
        expires_at=_parse_datetime(
            _optional_str(authorization_payload.get("expires_at"))
        ),
        user_id=_optional_str(authorization_payload.get("user_id")),
        user_name=_optional_str(authorization_payload.get("user_name")),
    )
    options = tuple(
        FacebookPageOption(
            page_id=str(option.get("page_id") or ""),
            page_name=str(option.get("page_name") or ""),
            page_access_token=str(option.get("page_access_token") or ""),
            instagram_business_account_id=_optional_str(
                option.get("instagram_business_account_id")
            ),
        )
        for option in options_payload
        if (
            option.get("page_id")
            and option.get("page_name")
            and option.get("page_access_token")
        )
    )
    return (authorization, options)


def build_facebook_page_payload(
    *,
    authorization: FacebookUserAuthorization,
    selected_page: FacebookPageOption,
) -> OAuthConnectedAccountPayload:
    return OAuthConnectedAccountPayload(
        provider_slug="facebook",
        provider_account_id=selected_page.page_id,
        account_type="facebook_page",
        display_name=selected_page.page_name,
        username=None,
        access_token=selected_page.page_access_token,
        refresh_token=None,
        token_type=authorization.token_type or "Bearer",
        scopes=authorization.scopes,
        expires_at=authorization.expires_at,
        refresh_expires_at=None,
        provider_metadata={
            "facebook_user_id": authorization.user_id,
            "facebook_user_name": authorization.user_name,
            "instagram_business_account_id": (
                selected_page.instagram_business_account_id
            ),
        },
    )


def _parse_json_response(
    response: httpx.Response,
    *,
    provider_label: str,
) -> dict[str, Any]:
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        detail = None
        try:
            detail = response.json()
        except ValueError:
            detail = response.text.strip() or None
        raise OAuthProviderError(
            f"{provider_label} OAuth request failed: {detail or exc}."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise OAuthProviderError(
            f"{provider_label} OAuth returned an unreadable response payload."
        ) from exc
    if not isinstance(payload, dict):
        raise OAuthProviderError(
            f"{provider_label} OAuth returned an unexpected response payload."
        )
    return payload


def _require_token(payload: dict[str, Any], *, provider_label: str) -> str:
    token = _optional_str(payload.get("access_token"))
    if token:
        return token
    raise OAuthProviderError(f"{provider_label} OAuth did not return an access token.")


def _normalize_scopes(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        cleaned = value.replace(",", " ").split()
        return tuple(dict.fromkeys(scope.strip() for scope in cleaned if scope.strip()))
    if isinstance(value, (list, tuple, set)):
        return tuple(
            dict.fromkeys(str(scope).strip() for scope in value if str(scope).strip())
        )
    return ()


def _split_scopes(value: str) -> tuple[str, ...]:
    return _normalize_scopes(value)


def _build_expiry_datetime(value: Any) -> datetime | None:
    try:
        expires_in = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.now(UTC) + timedelta(seconds=expires_in)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _load_json_value(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
