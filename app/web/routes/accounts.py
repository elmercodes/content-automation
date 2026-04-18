from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.accounts_service import (
    create_oauth_connection_attempt,
    delete_oauth_connection_attempt,
    disconnect_connected_account,
    generate_pkce_code_verifier,
    list_provider_runtime_states,
    load_oauth_connection_attempt,
    update_oauth_connection_attempt_payload,
    upsert_connected_account,
)
from app.config import get_settings
from app.db import get_session_factory
from app.oauth_clients import (
    OAuthProviderError,
    build_facebook_page_payload,
    build_provider_callback_url,
    deserialize_facebook_pending_payload,
    get_oauth_client,
    serialize_facebook_pending_payload,
)
from app.platforms import get_platform
from app.web.templates import render_page

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.get("/accounts", name="accounts", response_class=HTMLResponse)
async def accounts(
    request: Request,
    notice: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    session_factory = get_session_factory()
    with session_factory() as db:
        provider_states = list_provider_runtime_states(db)

    return render_page(
        request,
        "pages/accounts.html",
        page_title="Accounts",
        active_page="accounts",
        provider_states=provider_states,
        notice_message=notice,
        error_message=error,
    )


@router.get("/connect/{provider}", name="connect_provider")
async def connect_provider(request: Request, provider: str) -> Response:
    settings = get_settings()
    try:
        platform = get_platform(provider)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not platform.is_configured(settings):
        redirect_url = request.url_for("accounts").include_query_params(
            error=(
                f"{platform.display_name} is missing app-level provider settings in "
                ".env."
            )
        )
        return RedirectResponse(
            url=str(redirect_url),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    oauth_client = get_oauth_client(provider)
    code_verifier = (
        generate_pkce_code_verifier() if oauth_client.supports_pkce else None
    )
    session_factory = get_session_factory()
    with session_factory() as db:
        attempt = create_oauth_connection_attempt(
            db,
            provider_slug=provider,
            code_verifier=code_verifier,
            redirect_after=str(request.url_for("accounts")),
        )

    try:
        authorization_url = oauth_client.build_authorization_url(
            settings=settings,
            callback_url=build_provider_callback_url(settings, provider),
            state_token=attempt.state_token,
            code_verifier=code_verifier,
        )
    except OAuthProviderError as exc:
        redirect_url = request.url_for("accounts").include_query_params(error=str(exc))
        return RedirectResponse(
            url=str(redirect_url),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/oauth/callback/{provider}", name="oauth_callback")
async def oauth_callback(
    request: Request,
    provider: str,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> Response:
    settings = get_settings()
    session_factory = get_session_factory()

    with session_factory() as db:
        attempt = load_oauth_connection_attempt(
            db,
            provider_slug=provider,
            state_token=state,
        )
        if attempt is None:
            return _redirect_accounts(
                request,
                error="The OAuth callback state is missing or has expired.",
            )

        if error:
            delete_oauth_connection_attempt(db, attempt)
            return _redirect_accounts(
                request,
                error=error_description or error,
            )

        if not code:
            delete_oauth_connection_attempt(db, attempt)
            return _redirect_accounts(
                request,
                error="The provider callback did not return an authorization code.",
            )

        oauth_client = get_oauth_client(provider)
        try:
            exchanged = oauth_client.exchange_code(
                settings=settings,
                callback_url=build_provider_callback_url(settings, provider),
                code=code,
                code_verifier=attempt.code_verifier,
            )
        except OAuthProviderError as exc:
            delete_oauth_connection_attempt(db, attempt)
            return _redirect_accounts(request, error=str(exc))

        if provider == "facebook":
            authorization = exchanged
            try:
                page_options = oauth_client.load_page_options(
                    settings=settings,
                    authorization=authorization,
                )
            except OAuthProviderError as exc:
                logger.warning(
                    "Facebook page lookup failed during OAuth callback: %s",
                    exc,
                )
                delete_oauth_connection_attempt(db, attempt)
                return _redirect_accounts(request, error=str(exc))
            if not page_options:
                delete_oauth_connection_attempt(db, attempt)
                return _redirect_accounts(
                    request,
                    error=(
                        "Facebook login succeeded, but no manageable Pages were "
                        "available to connect."
                    ),
                )

            if len(page_options) == 1:
                payload = build_facebook_page_payload(
                    authorization=authorization,
                    selected_page=page_options[0],
                )
                upsert_connected_account(db, payload)
                delete_oauth_connection_attempt(db, attempt)
                return _redirect_accounts(
                    request,
                    notice=f"Connected {payload.display_name or 'Facebook Page'}.",
                )

            update_oauth_connection_attempt_payload(
                db,
                attempt,
                pending_payload_json=serialize_facebook_pending_payload(
                    authorization=authorization,
                    page_options=page_options,
                ),
            )
            select_page_url = request.url_for(
                "facebook_select_page"
            ).include_query_params(attempt_id=attempt.id)
            return RedirectResponse(
                url=str(select_page_url),
                status_code=status.HTTP_303_SEE_OTHER,
            )

        payload = exchanged
        upsert_connected_account(db, payload)
        delete_oauth_connection_attempt(db, attempt)
        return _redirect_accounts(
            request,
            notice=(
                f"Connected {payload.provider_slug.title()} "
                f"{payload.display_name or payload.username or 'account'}."
            ),
        )


@router.get(
    "/connect/facebook/select-page",
    name="facebook_select_page",
    response_class=HTMLResponse,
)
async def facebook_select_page(
    request: Request,
    attempt_id: int | None = None,
    error: str | None = None,
) -> HTMLResponse:
    if attempt_id is None:
        return _redirect_accounts(
            request,
            error="The Facebook Page selection state is missing.",
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        attempt = load_oauth_connection_attempt(
            db,
            provider_slug="facebook",
            attempt_id=attempt_id,
        )
        if attempt is None:
            return _redirect_accounts(
                request,
                error="The Facebook Page selection state has expired.",
            )
        _authorization, page_options = deserialize_facebook_pending_payload(
            attempt.pending_payload_json
        )

    return render_page(
        request,
        "pages/facebook_select_page.html",
        page_title="Choose Facebook Page",
        active_page="accounts",
        attempt_id=attempt_id,
        page_options=page_options,
        selection_error=error,
    )


@router.post("/connect/facebook/select-page", name="submit_facebook_select_page")
async def submit_facebook_select_page(request: Request) -> Response:
    form_data = await request.form()
    attempt_id = _parse_attempt_id(form_data.get("attempt_id"))
    selected_page_id = str(form_data.get("page_id") or "").strip()
    if attempt_id is None:
        return _redirect_accounts(
            request,
            error="The Facebook Page selection state is missing.",
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        attempt = load_oauth_connection_attempt(
            db,
            provider_slug="facebook",
            attempt_id=attempt_id,
        )
        if attempt is None:
            return _redirect_accounts(
                request,
                error="The Facebook Page selection state has expired.",
            )
        authorization, page_options = deserialize_facebook_pending_payload(
            attempt.pending_payload_json
        )
        selected_page = next(
            (
                page_option
                for page_option in page_options
                if page_option.page_id == selected_page_id
            ),
            None,
        )
        if selected_page is None:
            retry_url = request.url_for("facebook_select_page").include_query_params(
                attempt_id=attempt_id,
                error="Choose one Facebook Page before continuing.",
            )
            return RedirectResponse(
                url=str(retry_url),
                status_code=status.HTTP_303_SEE_OTHER,
            )

        payload = build_facebook_page_payload(
            authorization=authorization,
            selected_page=selected_page,
        )
        upsert_connected_account(db, payload)
        delete_oauth_connection_attempt(db, attempt)

    return _redirect_accounts(
        request,
        notice=f"Connected {payload.display_name or 'Facebook Page'}.",
    )


@router.post("/accounts/{provider}/disconnect", name="disconnect_provider")
async def disconnect_provider(request: Request, provider: str) -> Response:
    try:
        get_platform(provider)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_factory = get_session_factory()
    with session_factory() as db:
        disconnect_connected_account(db, provider_slug=provider)

    return _redirect_accounts(
        request,
        notice=f"Disconnected {provider.title()}.",
    )


def _parse_attempt_id(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _redirect_accounts(
    request: Request,
    *,
    notice: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    query_params: dict[str, str] = {}
    if notice:
        query_params["notice"] = notice
    if error:
        query_params["error"] = error
    url = request.url_for("accounts").include_query_params(**query_params)
    return RedirectResponse(
        url=str(url),
        status_code=status.HTTP_303_SEE_OTHER,
    )
