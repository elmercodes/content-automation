import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_homepage_renders(isolated_local_runtime) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get("/")

    assert response.status_code == 200
    assert "Local-First Social Publisher" in response.text
    assert "Draft once, review safely, and keep a local publishing ledger" in (
        response.text
    )


@pytest.mark.anyio
async def test_health_endpoint(isolated_local_runtime) -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app_configured_platforms"] == []
    assert response.json()["connected_platforms"] == []
