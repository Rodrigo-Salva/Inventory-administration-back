"""Fixtures de integración: API completa contra una base PostgreSQL de PRUEBAS (ver support.py)."""

from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from support import TEST_DATABASE_URL, database_available, ensure_migrated, reset_schema


@pytest.fixture
def migrated_database():
    if not database_available():
        pytest.skip("Base de pruebas no disponible")
    ensure_migrated()
    yield


@pytest.fixture
def blank_database():
    """Base de pruebas SIN esquema: para probar las migraciones desde cero."""
    if not database_available():
        pytest.skip("Base de pruebas no disponible")
    reset_schema()
    yield
    reset_schema()  # la siguiente prueba de API volverá a migrar


@pytest.fixture
async def api(monkeypatch, migrated_database) -> AsyncGenerator[AsyncClient, None]:
    from app.infrastructure.persistence.database import get_db
    from app.infrastructure.security.rate_limit import limiter
    from app.main import app
    from app.presentation.api.v1.sales import sales as sales_router

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # las tareas en segundo plano de ventas no deben tocar la base de desarrollo
    monkeypatch.setattr(sales_router, "async_session", session_factory)
    monkeypatch.setattr(limiter, "enabled", False)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()
