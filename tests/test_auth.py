import pytest
from httpx import AsyncClient
from app.presentation.api.v1.identity import auth as identity_http

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, monkeypatch):
    class InvalidCredentialsUseCase:
        async def execute(self, _email: str, _password: str):
            return None

    monkeypatch.setattr(
        identity_http, "_use_cases", lambda _db: (None, InvalidCredentialsUseCase())
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "wronguser@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Inventory SaaS API" in response.json()["message"]
