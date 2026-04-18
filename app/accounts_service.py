"""Local connected-account persistence and provider runtime state helpers."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import ConnectedAccount, OAuthConnectionAttempt
from app.oauth_clients import (
    OAuthConnectedAccountPayload,
    OAuthProviderError,
    get_oauth_client,
)
from app.platforms import PlatformDefinition, get_platform, get_supported_platforms

OAUTH_ATTEMPT_TTL_MINUTES = 15


@dataclass(frozen=True, slots=True)
class ConnectedAccountSummary:
    provider_slug: str
    provider_account_id: str | None
    account_type: str | None
    display_name: str | None
    username: str | None
    scopes: tuple[str, ...]
    connection_status: str
    expires_at: datetime | None
    refresh_expires_at: datetime | None
    last_validated_at: datetime | None
    last_used_at: datetime | None
    provider_metadata: dict[str, Any]

    @property
    def account_label(self) -> str:
        if self.display_name and self.username:
            return f"{self.display_name} (@{self.username})"
        if self.display_name:
            return self.display_name
        if self.username:
            return f"@{self.username}"
        if self.provider_account_id:
            return self.provider_account_id
        return "Connected account"


@dataclass(frozen=True, slots=True)
class ProviderRuntimeState:
    platform: PlatformDefinition
    app_configured: bool
    connectable: bool
    connected: bool
    ready_to_post: bool
    connection_status: str
    connection_message: str
    posting_status: str
    posting_message: str
    connected_account: ConnectedAccountSummary | None


def list_provider_runtime_states(
    session: Session,
    *,
    settings: Settings | None = None,
) -> tuple[ProviderRuntimeState, ...]:
    resolved_settings = settings or get_settings()
    return tuple(
        get_provider_runtime_state(
            session,
            platform.slug,
            settings=resolved_settings,
        )
        for platform in get_supported_platforms()
    )


def get_provider_runtime_state(
    session: Session,
    provider_slug: str,
    *,
    settings: Settings | None = None,
) -> ProviderRuntimeState:
    resolved_settings = settings or get_settings()
    platform = get_platform(provider_slug)
    app_configured = platform.is_configured(resolved_settings)
    account = get_connected_account_summary(
        session,
        provider_slug=provider_slug,
        settings=resolved_settings,
        ensure_active=True,
    )

    if not app_configured:
        missing_settings = ", ".join(platform.missing_settings(resolved_settings))
        return ProviderRuntimeState(
            platform=platform,
            app_configured=False,
            connectable=False,
            connected=False,
            ready_to_post=False,
            connection_status="not_configured",
            connection_message=(
                f"Add app-level provider settings in .env first: {missing_settings}."
            ),
            posting_status="not_configured",
            posting_message=(
                f"{platform.display_name} cannot be used until app-level provider "
                "settings are configured."
            ),
            connected_account=None,
        )

    if account is None:
        return ProviderRuntimeState(
            platform=platform,
            app_configured=True,
            connectable=True,
            connected=False,
            ready_to_post=False,
            connection_status="not_connected",
            connection_message=(
                f"Connect a {platform.display_name} account from the Accounts page."
            ),
            posting_status="not_connected",
            posting_message=(
                f"{platform.display_name} is not ready because no connected account "
                "is available."
            ),
            connected_account=None,
        )

    if account.connection_status == "reauthorization_required":
        return ProviderRuntimeState(
            platform=platform,
            app_configured=True,
            connectable=True,
            connected=False,
            ready_to_post=False,
            connection_status="reauthorization_required",
            connection_message=(
                f"Reconnect {platform.display_name} to restore local access."
            ),
            posting_status="reauthorization_required",
            posting_message=(
                f"{platform.display_name} requires reauthorization before it can "
                "be used."
            ),
            connected_account=account,
        )

    if not platform.posting_spec.enabled:
        posting_status = "unsupported"
        posting_message = platform.posting_spec.notes
    elif _missing_posting_scopes(account, platform):
        posting_status = "reauthorization_required"
        posting_message = (
            f"Reconnect {platform.display_name} to grant: "
            f"{', '.join(_missing_posting_scopes(account, platform))}."
        )
    else:
        posting_status = "ready"
        posting_message = (
            f"{platform.display_name} is ready to post with {account.account_label}."
        )
    return ProviderRuntimeState(
        platform=platform,
        app_configured=True,
        connectable=True,
        connected=True,
        ready_to_post=posting_status == "ready",
        connection_status="connected",
        connection_message=f"Connected to {account.account_label}.",
        posting_status=posting_status,
        posting_message=posting_message,
        connected_account=account,
    )


def get_connected_account_summary(
    session: Session,
    *,
    provider_slug: str,
    settings: Settings | None = None,
    ensure_active: bool = False,
) -> ConnectedAccountSummary | None:
    account = load_connected_account(
        session,
        provider_slug=provider_slug,
        settings=settings,
        ensure_active=ensure_active,
    )
    if account is None:
        return None
    return summarize_connected_account(account)


def load_connected_account(
    session: Session,
    *,
    provider_slug: str,
    settings: Settings | None = None,
    ensure_active: bool = False,
) -> ConnectedAccount | None:
    account = session.scalar(
        select(ConnectedAccount).where(ConnectedAccount.provider_slug == provider_slug)
    )
    if account is None:
        return None
    if ensure_active:
        return ensure_connected_account_active(
            session,
            provider_slug=provider_slug,
            settings=settings,
        )
    return account


def summarize_connected_account(account: ConnectedAccount) -> ConnectedAccountSummary:
    return ConnectedAccountSummary(
        provider_slug=account.provider_slug,
        provider_account_id=account.provider_account_id,
        account_type=account.account_type,
        display_name=account.display_name,
        username=account.username,
        scopes=_split_scopes(account.scopes),
        connection_status=account.connection_status,
        expires_at=account.expires_at,
        refresh_expires_at=account.refresh_expires_at,
        last_validated_at=account.last_validated_at,
        last_used_at=account.last_used_at,
        provider_metadata=_load_json_value(account.provider_metadata_json),
    )


def upsert_connected_account(
    session: Session,
    payload: OAuthConnectedAccountPayload,
) -> ConnectedAccount:
    account = session.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.provider_slug == payload.provider_slug
        )
    )
    if account is None:
        account = ConnectedAccount(provider_slug=payload.provider_slug)
        session.add(account)

    now = _utcnow()
    account.provider_account_id = payload.provider_account_id
    account.account_type = payload.account_type
    account.display_name = payload.display_name
    account.username = payload.username
    account.access_token = payload.access_token
    account.refresh_token = payload.refresh_token
    account.token_type = payload.token_type
    account.scopes = ",".join(payload.scopes)
    account.expires_at = payload.expires_at
    account.refresh_expires_at = payload.refresh_expires_at
    account.connection_status = "active"
    account.provider_metadata_json = json.dumps(
        payload.provider_metadata,
        sort_keys=True,
    )
    account.last_validated_at = now
    account.last_used_at = None
    account.updated_at = now

    session.commit()
    session.refresh(account)
    return account


def disconnect_connected_account(
    session: Session,
    *,
    provider_slug: str,
) -> ConnectedAccount | None:
    account = session.scalar(
        select(ConnectedAccount).where(ConnectedAccount.provider_slug == provider_slug)
    )
    if account is None:
        return None

    now = _utcnow()
    account.access_token = None
    account.refresh_token = None
    account.token_type = None
    account.scopes = ""
    account.expires_at = None
    account.refresh_expires_at = None
    account.connection_status = "disconnected"
    account.last_validated_at = now
    account.updated_at = now
    session.commit()
    session.refresh(account)
    return account


def mark_connected_account_used(
    session: Session,
    account: ConnectedAccount,
) -> ConnectedAccount:
    account.last_used_at = _utcnow()
    account.updated_at = account.last_used_at
    session.commit()
    session.refresh(account)
    return account


def ensure_connected_account_active(
    session: Session,
    *,
    provider_slug: str,
    settings: Settings | None = None,
) -> ConnectedAccount | None:
    resolved_settings = settings or get_settings()
    account = session.scalar(
        select(ConnectedAccount).where(ConnectedAccount.provider_slug == provider_slug)
    )
    if account is None:
        return None
    if account.connection_status == "disconnected":
        return None
    if account.connection_status == "reauthorization_required":
        return account
    if not account.access_token:
        account.connection_status = "reauthorization_required"
        account.last_validated_at = _utcnow()
        session.commit()
        session.refresh(account)
        return account

    if not _token_is_expired(account.expires_at):
        return account

    client = get_oauth_client(provider_slug)
    if not client.supports_refresh or not account.refresh_token:
        account.connection_status = "reauthorization_required"
        account.last_validated_at = _utcnow()
        account.updated_at = account.last_validated_at
        session.commit()
        session.refresh(account)
        return account

    try:
        refreshed_payload = client.refresh_connected_account(
            settings=resolved_settings,
            account=account,
        )
    except OAuthProviderError:
        account.connection_status = "reauthorization_required"
        account.last_validated_at = _utcnow()
        account.updated_at = account.last_validated_at
        session.commit()
        session.refresh(account)
        return account

    if refreshed_payload is None:
        return account
    return upsert_connected_account(session, refreshed_payload)


def create_oauth_connection_attempt(
    session: Session,
    *,
    provider_slug: str,
    code_verifier: str | None = None,
    redirect_after: str | None = None,
    pending_payload_json: str | None = None,
) -> OAuthConnectionAttempt:
    cleanup_expired_oauth_connection_attempts(session)
    attempt = OAuthConnectionAttempt(
        provider_slug=provider_slug,
        state_token=secrets.token_urlsafe(24),
        code_verifier=code_verifier,
        redirect_after=redirect_after,
        pending_payload_json=pending_payload_json,
        expires_at=_utcnow() + timedelta(minutes=OAUTH_ATTEMPT_TTL_MINUTES),
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt


def load_oauth_connection_attempt(
    session: Session,
    *,
    provider_slug: str,
    state_token: str | None = None,
    attempt_id: int | None = None,
) -> OAuthConnectionAttempt | None:
    statement = select(OAuthConnectionAttempt).where(
        OAuthConnectionAttempt.provider_slug == provider_slug
    )
    if state_token is not None:
        statement = statement.where(OAuthConnectionAttempt.state_token == state_token)
    if attempt_id is not None:
        statement = statement.where(OAuthConnectionAttempt.id == attempt_id)
    attempt = session.scalar(statement)
    if attempt is None:
        return None
    if _normalize_datetime(attempt.expires_at) <= _utcnow():
        session.delete(attempt)
        session.commit()
        return None
    return attempt


def update_oauth_connection_attempt_payload(
    session: Session,
    attempt: OAuthConnectionAttempt,
    *,
    pending_payload_json: str,
) -> OAuthConnectionAttempt:
    attempt.pending_payload_json = pending_payload_json
    session.commit()
    session.refresh(attempt)
    return attempt


def delete_oauth_connection_attempt(
    session: Session,
    attempt: OAuthConnectionAttempt,
) -> None:
    session.delete(attempt)
    session.commit()


def cleanup_expired_oauth_connection_attempts(session: Session) -> None:
    now = _utcnow()
    attempts = session.scalars(
        select(OAuthConnectionAttempt).where(OAuthConnectionAttempt.expires_at <= now)
    ).all()
    if not attempts:
        return
    for attempt in attempts:
        session.delete(attempt)
    session.commit()


def generate_pkce_code_verifier() -> str:
    return secrets.token_urlsafe(48)


def _account_is_posting_ready(
    account: ConnectedAccountSummary,
    platform: PlatformDefinition,
) -> bool:
    if account.connection_status != "active":
        return False
    if not platform.posting_spec.enabled:
        return False
    return not _missing_posting_scopes(account, platform)


def _missing_posting_scopes(
    account: ConnectedAccountSummary,
    platform: PlatformDefinition,
) -> tuple[str, ...]:
    required_scopes = set(platform.posting_spec.required_scopes)
    return tuple(sorted(required_scopes - set(account.scopes)))


def _token_is_expired(expires_at: datetime | None) -> bool:
    return expires_at is not None and _normalize_datetime(expires_at) <= _utcnow()


def _split_scopes(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(scope for scope in value.split(",") if scope)


def _load_json_value(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
