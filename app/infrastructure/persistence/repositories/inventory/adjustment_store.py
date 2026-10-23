from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inventory.dto import CreateAdjustmentCommand, StockProduct
from app.application.shared.ports import TaskScheduler
from app.infrastructure.persistence.models.inventory.adjustment import AdjustmentReason, InventoryAdjustment
from app.infrastructure.persistence.repositories.inventory.branch_ledger import SqlAlchemyBranchLedger
from app.infrastructure.persistence.repositories.inventory.branch_resolver import SqlAlchemyBranchResolver


class SqlAlchemyAdjustmentStore:
    """Adaptador SQLAlchemy del puerto AdjustmentStore: el ajuste opera sobre el stock de UNA sucursal."""

    def __init__(self, db: AsyncSession, scheduler: TaskScheduler | None = None):
        self.db = db
        self.ledger = SqlAlchemyBranchLedger(db, scheduler)
        self.branches = SqlAlchemyBranchResolver(db)

    async def _branch(self, tenant_id: int, branch_id: int | None) -> int:
        return branch_id if branch_id is not None else await self.branches.resolve(tenant_id, None)

    async def lock_product(
        self, tenant_id: int, product_id: int, branch_id: int | None = None
    ) -> StockProduct | None:
        position = await self.ledger.open_position(tenant_id, product_id, await self._branch(tenant_id, branch_id))
        return StockProduct(position.product_id, position.name, position.stock) if position else None

    async def record(
        self, command: CreateAdjustmentCommand, delta: int, stock_before: int, branch_id: int | None = None
    ) -> int:
        branch_id = await self._branch(command.tenant_id, branch_id)
        adjustment = InventoryAdjustment(
            tenant_id=command.tenant_id,
            user_id=command.user_id,
            product_id=command.product_id,
            adjustment_type=command.adjustment_type,
            quantity=command.quantity,
            reason=AdjustmentReason(command.reason),
            notes=command.notes,
        )
        self.db.add(adjustment)
        await self.ledger.post(
            command.tenant_id, command.user_id, command.product_id, branch_id, delta, "adjustment",
            reference=f"ADJ-{command.reason}", notes=command.notes,
        )
        await self.db.flush()
        return adjustment.id
