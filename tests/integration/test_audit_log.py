import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.persistence import audit_listener
from app.infrastructure.persistence.models.identity.user import User

def test_sensitive_columns_are_redacted():
    user = User(email="a@example.com", hashed_password="$2b$12$secret-hash", tenant_id=1)
    data = audit_listener.extract_model_data(user)
    assert data["hashed_password"] == "***" and data["email"] == "a@example.com"
    assert audit_listener.redact("secret_key", "abc") == "***"
    assert audit_listener.redact("secret_key", None) is None


async def test_audit_log_row_is_persisted(api, monkeypatch):
    """Regresión: el INSERT omitía updated_at (NOT NULL) y ningún registro de auditoría se guardaba."""
    import app.infrastructure.persistence.database as database
    from app.infrastructure.persistence.database import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    session = None
    async for session in override():  # sesión del motor de pruebas
        break
    factory = async_sessionmaker(session.bind, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session", factory)

    register = await api.post("/api/v1/auth/register", json={"email": "aud@example.com", "password": "password123"})
    tenant_id = register.json()["tenant_id"]

    await audit_listener.create_audit_log_async(
        "CREATE", {}, "Product", 7, tenant_id, None, "127.0.0.1", "pytest",
        None, {"name": "Café", "hashed_password": "***"},
    )
    async with factory() as check:
        row = (await check.execute(text(
            "select action, entity_type, entity_id, updated_at is not null from audit_logs where tenant_id=:t"
        ), {"t": tenant_id})).one()
    assert tuple(row) == ("CREATE", "Product", 7, True)
