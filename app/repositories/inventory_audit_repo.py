from typing import List, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from .base_repository import BaseRepository
from ..models.inventory_audit import InventoryAudit, InventoryAuditItem, AuditStatus
from ..core.pagination import PaginationParams

class InventoryAuditRepository(BaseRepository[InventoryAudit]):
    def __init__(self, db: AsyncSession):
        super().__init__(InventoryAudit, db)

    async def get_by_branch(self, branch_id: int, tenant_id: int) -> List[InventoryAudit]:
        from sqlalchemy.orm import selectinload
        query = select(InventoryAudit).options(
            selectinload(InventoryAudit.items).selectinload(InventoryAuditItem.product)
        ).where(
            and_(
                InventoryAudit.branch_id == branch_id,
                InventoryAudit.tenant_id == tenant_id
            )
        ).order_by(InventoryAudit.started_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_items(self, audit_id: int, tenant_id: int) -> Optional[InventoryAudit]:
        from sqlalchemy.orm import selectinload
        query = select(InventoryAudit).options(
            selectinload(InventoryAudit.items).selectinload(InventoryAuditItem.product)
        ).where(
            and_(
                InventoryAudit.id == audit_id,
                InventoryAudit.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_item(self, item_data: dict) -> InventoryAuditItem:
        item = InventoryAuditItem(**item_data)
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_recent(self, tenant_id: int, limit: int = 20) -> List[InventoryAudit]:
        from sqlalchemy.orm import joinedload, selectinload
        query = select(InventoryAudit).options(
            joinedload(InventoryAudit.branch),
            selectinload(InventoryAudit.items).selectinload(InventoryAuditItem.product)
        ).where(
            InventoryAudit.tenant_id == tenant_id
        ).order_by(InventoryAudit.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
