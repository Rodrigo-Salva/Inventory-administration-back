import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "inventory-saas"}


@pytest.mark.asyncio
async def test_health_root_path_used_by_docker_healthcheck(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
