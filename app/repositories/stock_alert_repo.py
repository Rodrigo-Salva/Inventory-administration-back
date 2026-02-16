from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .base_repository import BaseRepository
from ..models import StockAlert, AlertType, AlertStatus


class StockAlertRepository(BaseRepository[StockAlert]):
    """Repositorio para alertas de stock"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(StockAlert, db)
    
    async def get_active_alerts(self, tenant_id: int) -> List[StockAlert]:
        """Obtiene alertas activas"""
        query = select(StockAlert).where(
            and_(
                StockAlert.tenant_id == tenant_id,
                StockAlert.status == AlertStatus.ACTIVE
            )
        ).options(
            selectinload(StockAlert.product)
        ).order_by(StockAlert.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_product(self, product_id: int, tenant_id: int) -> List[StockAlert]:
        """Obtiene alertas de un producto"""
        query = select(StockAlert).where(
            and_(
                StockAlert.tenant_id == tenant_id,
                StockAlert.product_id == product_id
            )
        ).order_by(StockAlert.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_unnotified_alerts(self, tenant_id: int) -> List[StockAlert]:
        """Obtiene alertas activas no notificadas"""
        query = select(StockAlert).where(
            and_(
                StockAlert.tenant_id == tenant_id,
                StockAlert.status == AlertStatus.ACTIVE,
                StockAlert.is_notified == False
            )
        ).options(
            selectinload(StockAlert.product)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_as_notified(self, alert_ids: List[int]) -> None:
        """Marca alertas como notificadas"""
        for alert_id in alert_ids:
            alert = await self.get_by_id(alert_id)
            if alert:
                alert.is_notified = True
        await self.db.flush()
