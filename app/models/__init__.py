from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

Base = declarative_base()

engine = create_async_engine(settings.database_url, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Importar todos los modelos para que Alembic los detecte
from .tenant import Tenant
from .user import User
from .product import Product
from .category import Category
from .supplier import Supplier
from .inventory_movement import InventoryMovement, MovementType
from .stock_alert import StockAlert, AlertType, AlertStatus
from .audit_log import AuditLog

__all__ = [
    "Base",
    "get_db",
    "Tenant",
    "User",
    "Product",
    "Category",
    "Supplier",
    "InventoryMovement",
    "MovementType",
    "StockAlert",
    "AlertType",
    "AlertStatus",
    "AuditLog",
]