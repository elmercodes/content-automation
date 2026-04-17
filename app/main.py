from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.web import router
from app.web.templates import render_page

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    for path in settings.local_storage_paths:
        path.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Local-First Social Publisher",
        summary="Local-only social publishing foundation with server-rendered HTML.",
        lifespan=lifespan,
    )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> Response:
        if _should_render_html_error(request):
            error_title, error_message = _build_error_page_copy(exc)
            return render_page(
                request,
                "pages/error.html",
                page_title=error_title,
                active_page=_resolve_error_active_page(request),
                status_code=exc.status_code,
                error_status_code=exc.status_code,
                error_title=error_title,
                error_message=error_message,
            )

        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
    app.include_router(router)
    return app


app = create_app()


def _should_render_html_error(request: Request) -> bool:
    return not request.url.path.startswith(("/health", "/media/", "/static/"))


def _resolve_error_active_page(request: Request) -> str:
    if request.url.path.startswith("/history"):
        return "history"
    if request.url.path.startswith(("/compose", "/platforms", "/review", "/results")):
        return "compose"
    return "home"


def _build_error_page_copy(exc: StarletteHTTPException) -> tuple[str, str]:
    detail = str(exc.detail).strip() if exc.detail else ""
    if exc.status_code == 404:
        if detail and detail != "Not Found":
            return ("Page not found", detail)
        return (
            "Page not found",
            "The page or local record you requested could not be found.",
        )
    if exc.status_code == 405:
        return (
            "Request method not allowed",
            "This page does not support that type of request.",
        )
    if detail:
        return ("Request could not be completed", detail)
    return (
        "Request could not be completed",
        "The app could not finish that request.",
    )
