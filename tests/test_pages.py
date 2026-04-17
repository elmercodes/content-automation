import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "expected_text"),
    [
        ("/", "Platform selection and workflow handoff"),
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
