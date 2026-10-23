from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.infrastructure.persistence.models.inventory.stock_transfer import StockTransfer, StockTransferItem, StockTransferStatus
from typing import List, Optional

class StockTransferRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[StockTransfer]:
        query = select(StockTransfer).where(StockTransfer.tenant_id == tenant_id)\
            .options(
                selectinload(StockTransfer.from_branch),
                selectinload(StockTransfer.to_branch),
                selectinload(StockTransfer.user),
                selectinload(StockTransfer.items).selectinload(StockTransferItem.product)
            )\
            .order_by(StockTransfer.created_at.desc())\
            .offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, transfer_id: int, tenant_id: int) -> Optional[StockTransfer]:
        query = select(StockTransfer).where(
            and_(StockTransfer.id == transfer_id, StockTransfer.tenant_id == tenant_id)
        ).options(
            selectinload(StockTransfer.from_branch),
            selectinload(StockTransfer.to_branch),
            selectinload(StockTransfer.user),
            selectinload(StockTransfer.items).selectinload(StockTransferItem.product)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_stats(self, tenant_id: int) -> dict:
        """Calcula estadísticas generales de traslados para el tenant"""
        from sqlalchemy import func
        query = select(
            func.count(StockTransfer.id).label("total_count"),
            func.count(StockTransfer.id).filter(StockTransfer.status == StockTransferStatus.PENDING).label("pending_count"),
            func.count(StockTransfer.id).filter(StockTransfer.status == StockTransferStatus.COMPLETED).label("completed_count"),
            func.count(StockTransfer.id).filter(StockTransfer.status == StockTransferStatus.CANCELLED).label("cancelled_count")
        ).where(StockTransfer.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        row = result.fetchone()
        
        return {
            "total_count": row.total_count or 0,
            "pending_count": row.pending_count or 0,
            "completed_count": row.completed_count or 0,
            "cancelled_count": row.cancelled_count or 0
        }
