from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.inventory.dto import CreateTransferCommand, TransferItem, TransferSnapshot
from app.infrastructure.persistence.models.inventory.stock_transfer import (
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)


class SqlAlchemyTransferStore:
    """Adaptador SQLAlchemy del puerto TransferStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, command: CreateTransferCommand) -> int:
        transfer = StockTransfer(
            tenant_id=command.tenant_id,
            from_branch_id=command.from_branch_id,
            to_branch_id=command.to_branch_id,
            user_id=command.user_id,
            notes=command.notes,
            reference=command.reference,
            status=StockTransferStatus.PENDING,
        )
        self.db.add(transfer)
        await self.db.flush()
        for item in command.items:
            self.db.add(
                StockTransferItem(
                    transfer_id=transfer.id,
                    product_id=item.product_id,
                    batch_id=item.batch_id,
                    quantity=item.quantity,
                )
            )
        await self.db.flush()
        return transfer.id

    async def get(self, tenant_id: int, transfer_id: int) -> TransferSnapshot | None:
        result = await self.db.execute(
            select(StockTransfer)
            .options(selectinload(StockTransfer.items))
            .where(StockTransfer.id == transfer_id, StockTransfer.tenant_id == tenant_id)
            .with_for_update()
        )
        transfer = result.scalar_one_or_none()
        if not transfer:
            return None
        return TransferSnapshot(
            id=transfer.id,
            user_id=transfer.user_id,
            status=str(getattr(transfer.status, "value", transfer.status)),
            from_branch_id=transfer.from_branch_id,
            to_branch_id=transfer.to_branch_id,
            items=tuple(TransferItem(i.product_id, i.quantity, i.batch_id) for i in transfer.items),
        )

    async def mark_completed(self, transfer_id: int) -> None:
        transfer = await self.db.get(StockTransfer, transfer_id)
        transfer.status = StockTransferStatus.COMPLETED
        transfer.completed_at = datetime.utcnow()
        await self.db.flush()

    async def mark_cancelled(self, transfer_id: int) -> None:
        transfer = await self.db.get(StockTransfer, transfer_id)
        transfer.status = StockTransferStatus.CANCELLED
        transfer.cancelled_at = datetime.utcnow()
        await self.db.flush()
