from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inventory.dto import StockPosition
from app.infrastructure.persistence.repositories.inventory.stock_alerts import build_stock_alerts, level_of
from app.application.shared.ports import TaskScheduler
from app.infrastructure.persistence.models.catalog.product import Product
from app.infrastructure.persistence.models.inventory.inventory_movement import (
    InventoryMovement,
    MovementType,
)
from app.infrastructure.persistence.models.inventory.product_branch import ProductBranch


class SqlAlchemyBranchLedger:
    """Adaptador SQLAlchemy de BranchLedger: stock por sucursal + total del producto + kardex."""

    def __init__(self, db: AsyncSession, scheduler: TaskScheduler | None = None):
        self.db = db
        self.scheduler = scheduler
        self.alerts = build_stock_alerts(db)

    async def _product(self, tenant_id: int, product_id: int) -> Product | None:
        result = await self.db.execute(
            select(Product)
            .where(Product.id == product_id, Product.tenant_id == tenant_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def _branch_stock(self, product_id: int, branch_id: int) -> ProductBranch | None:
        result = await self.db.execute(
            select(ProductBranch)
            .where(ProductBranch.product_id == product_id, ProductBranch.branch_id == branch_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def open_position(
        self,
        tenant_id: int,
        product_id: int,
        branch_id: int,
        aisle: str | None = None,
        shelf: str | None = None,
        bin: str | None = None,
    ) -> StockPosition | None:
        product = await self._product(tenant_id, product_id)
        if not product:
            return None
        position = await self._branch_stock(product_id, branch_id)
        if not position:
            position = ProductBranch(
                product_id=product_id,
                branch_id=branch_id,
                stock=0,
                min_stock=product.min_stock,
                max_stock=product.max_stock,
            )
            self.db.add(position)
        if aisle is not None:
            position.aisle = aisle
        if shelf is not None:
            position.shelf = shelf
        if bin is not None:
            position.bin = bin
        await self.db.flush()
        return StockPosition(product.id, product.name, position.stock)

    async def current_stock(self, tenant_id: int, product_id: int, branch_id: int) -> int:
        position = await self._branch_stock(product_id, branch_id)
        return position.stock if position else 0

    async def post(
        self,
        tenant_id: int,
        user_id: int,
        product_id: int,
        branch_id: int,
        delta: int,
        movement_type: str,
        unit_cost: object = None,
        reference: str | None = None,
        notes: str | None = None,
        batch_id: int | None = None,
    ) -> int:
        product = await self._product(tenant_id, product_id)
        position = await self._branch_stock(product_id, branch_id)

        stock_before = position.stock
        position.stock += delta
        product.stock += delta  # el total del producto es la suma de sus sucursales

        movement = InventoryMovement(
            tenant_id=tenant_id,
            product_id=product_id,
            branch_id=branch_id,
            batch_id=batch_id,
            user_id=user_id,
            movement_type=MovementType(movement_type),
            quantity=delta,
            stock_before=stock_before,
            stock_after=position.stock,
            unit_cost=unit_cost if unit_cost is not None else product.cost,
            reference=reference,
            notes=notes,
        )
        self.db.add(movement)
        await self.db.flush()

        if delta < 0:
            await self.alerts.check(level_of(product), tenant_id, self.scheduler)
        else:
            await self.alerts.resolve_if_recovered(level_of(product), tenant_id)
        return movement.id
