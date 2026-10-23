import pytest
import os
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.infrastructure.persistence.database import get_db
from app.infrastructure.config import settings

# Nunca usar la base de desarrollo para pruebas. CI y docker-compose.test
# declaran TEST_DATABASE_URL; el fallback solo construye un nombre separado.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    base_url, separator, database_name = settings.database_url.rpartition("/")
    if not separator or not database_name:
        raise RuntimeError("Define TEST_DATABASE_URL para ejecutar las pruebas.")
    TEST_DATABASE_URL = f"{base_url}/{database_name}_test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
