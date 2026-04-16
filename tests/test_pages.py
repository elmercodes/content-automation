import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "expected_text"),
    [
        ("/", "Database layer and migration foundation"),
        ("/compose", "Master post shell"),
        ("/platforms", "No platforms are configured locally"),
        ("/review/platforms", "Future platform-aware checks"),
        ("/review/final", "Submission checkpoint shell"),
        ("/results", "Post platform log placeholder"),
        ("/history", "Local history placeholder"),
    ],
)
async def test_phase_three_pages_render(path: str, expected_text: str) -> None:
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
