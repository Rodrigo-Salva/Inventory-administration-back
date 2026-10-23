from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.purchasing.dto import CreatePurchaseCommand, PurchaseItemInput, PurchaseSnapshot
from app.infrastructure.persistence.models.purchasing.purchase import (
    Purchase,
    PurchaseItem,
    PurchaseStatus,
)


class SqlAlchemyPurchaseStore:
    """Adaptador SQLAlchemy del puerto PurchaseStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, command: CreatePurchaseCommand, total: Decimal) -> int:
        purchase = Purchase(
            tenant_id=command.tenant_id,
            user_id=command.user_id,
            supplier_id=command.supplier_id,
            branch_id=command.branch_id,
            reference_number=command.reference_number,
            notes=command.notes,
            due_date=command.due_date,
            total_amount=total,
        )
        self.db.add(purchase)
        await self.db.flush()
        for item in command.items:
            self.db.add(
                PurchaseItem(
                    purchase_id=purchase.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    subtotal=Decimal(item.quantity) * item.unit_cost,
                )
            )
        await self.db.flush()
        return purchase.id

    async def get(self, tenant_id: int, purchase_id: int) -> PurchaseSnapshot | None:
        result = await self.db.execute(
            select(Purchase)
            .options(selectinload(Purchase.items))
            .where(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id)
            .with_for_update()
        )
        purchase = result.scalar_one_or_none()
        if not purchase:
            return None
        return PurchaseSnapshot(
            id=purchase.id,
            status=str(getattr(purchase.status, "value", purchase.status)),
            branch_id=purchase.branch_id,
            reference_number=purchase.reference_number,
            items=tuple(
                PurchaseItemInput(i.product_id, i.quantity, i.unit_cost) for i in purchase.items
            ),
        )

    async def mark_received(self, purchase_id: int) -> None:
        purchase = await self.db.get(Purchase, purchase_id)
        purchase.status = PurchaseStatus.RECEIVED
        await self.db.flush()

    async def mark_cancelled(self, purchase_id: int) -> None:
        purchase = await self.db.get(Purchase, purchase_id)
        purchase.status = PurchaseStatus.CANCELLED
        await self.db.flush()
