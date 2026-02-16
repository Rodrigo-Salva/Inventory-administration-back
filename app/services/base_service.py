from typing import Generic, TypeVar, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.logging_config import get_logger

logger = get_logger(__name__)

ServiceType = TypeVar("ServiceType")


class BaseService(Generic[ServiceType]):
    """Servicio base con lógica común"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger
    
    async def commit(self):
        """Commit de la transacción"""
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error en commit: {e}")
            raise
    
    async def rollback(self):
        """Rollback de la transacción"""
        await self.db.rollback()
