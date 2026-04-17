import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "expected_text"),
    [
        ("/", "Draft once, review safely, and keep a local publishing ledger"),
        ("/compose", "Create a master post"),
        ("/platforms", "Save a master post before choosing platforms"),
        ("/review/platforms", "Preview selected platforms"),
        ("/review/final", "Submission checkpoint"),
        ("/results", "Submission results"),
        ("/history", "Local content ledger"),
    ],
)
async def test_workflow_pages_render(path: str, expected_text: str) -> None:
    get_settings.cache_clear()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get(path)

    assert response.status_code == 200
    assert expected_text in response.text


@pytest.mark.anyio
async def test_unknown_page_renders_html_not_found_state() -> None:
    get_settings.cache_clear()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get("/missing-page")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "Page not found" in response.text
    assert "Return home" in response.text
