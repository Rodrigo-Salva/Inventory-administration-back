from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.inventory.dto import AuditItemSnapshot, AuditSnapshot, StartAuditCommand
from app.infrastructure.persistence.models.inventory.inventory_audit import (
    AuditStatus,
    InventoryAudit,
    InventoryAuditItem,
)


class SqlAlchemyAuditStore:
    """Adaptador SQLAlchemy del puerto AuditStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, command: StartAuditCommand) -> int:
        audit = InventoryAudit(
            tenant_id=command.tenant_id,
            branch_id=command.branch_id,
            user_id=command.user_id,
            notes=command.notes,
            status=AuditStatus.IN_PROGRESS.value,
            started_at=datetime.utcnow(),
        )
        self.db.add(audit)
        await self.db.flush()
        return audit.id

    async def get(self, tenant_id: int, audit_id: int) -> AuditSnapshot | None:
        result = await self.db.execute(
            select(InventoryAudit)
            .options(selectinload(InventoryAudit.items))
            .where(InventoryAudit.id == audit_id, InventoryAudit.tenant_id == tenant_id)
            .with_for_update()
        )
        audit = result.scalar_one_or_none()
        if not audit:
            return None
        return AuditSnapshot(
            id=audit.id,
            branch_id=audit.branch_id,
            status=str(getattr(audit.status, "value", audit.status)),
            items=tuple(
                AuditItemSnapshot(i.id, i.product_id, i.counted_stock, i.difference, bool(i.is_adjusted))
                for i in audit.items
            ),
        )

    async def upsert_item(
        self, audit_id: int, product_id: int, expected: int, counted: int, notes: str | None
    ) -> int:
        result = await self.db.execute(
            select(InventoryAuditItem).where(
                InventoryAuditItem.audit_id == audit_id, InventoryAuditItem.product_id == product_id
            )
        )
        item = result.scalar_one_or_none()
        if item:
            item.expected_stock = expected
            item.counted_stock = counted
            item.difference = counted - expected
            item.notes = notes
        else:
            item = InventoryAuditItem(
                audit_id=audit_id,
                product_id=product_id,
                expected_stock=expected,
                counted_stock=counted,
                difference=counted - expected,
                notes=notes,
            )
            self.db.add(item)
        await self.db.flush()
        return item.id

    async def mark_item_adjusted(self, item_id: int) -> None:
        item = await self.db.get(InventoryAuditItem, item_id)
        item.is_adjusted = True
        await self.db.flush()

    async def complete(self, audit_id: int) -> None:
        audit = await self.db.get(InventoryAudit, audit_id)
        audit.status = AuditStatus.COMPLETED.value
        audit.completed_at = datetime.utcnow()
        await self.db.flush()
