from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
import os

# Base de datos async
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:28demarzo@localhost:5432/inventory_saas")
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.utcnow, nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class TenantMixin:
    @declared_attr
    def tenant_id(cls):
        return Column(Integer, index=True, nullable=False)

class SoftDeleteMixin:
    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, nullable=False)
