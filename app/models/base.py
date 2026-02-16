from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from ..core.config import settings

# Crear Base declarativa
Base = declarative_base()

# Crear engine asíncrono
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow
)

# Crear session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Dependency para obtener sesión de BD
async def get_db():
    """Dependency para obtener sesión de BD"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


class TimestampMixin:
    """Mixin para agregar timestamps automáticos a los modelos"""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Mixin para implementar soft delete"""
    
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    def soft_delete(self):
        """Marca el registro como eliminado"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restaura un registro eliminado"""
        self.is_deleted = False
        self.deleted_at = None


class TenantMixin:
    """Mixin para multi-tenancy"""
    
    @declared_attr
    def tenant_id(cls):
        from sqlalchemy import Column, Integer, ForeignKey
        return Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
