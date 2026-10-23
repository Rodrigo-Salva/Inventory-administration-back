from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inventory.dto import TransferItem
from app.domain.inventory.errors import ProductNotFoundError
from app.infrastructure.persistence.repositories.inventory.branch_ledger import SqlAlchemyBranchLedger
from app.infrastructure.persistence.models.catalog.product import Product
from app.infrastructure.persistence.models.inventory.inventory_movement import (
    InventoryMovement,
    MovementType,
)
from app.infrastructure.persistence.models.inventory.product_branch import ProductBranch


class SqlAlchemyBranchStock:
    """Adaptador SQLAlchemy de BranchStockPort y StockReceiptPort (stock por sucursal)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _product_branch(self, product_id: int, branch_id: int) -> ProductBranch:
        result = await self.db.execute(
            select(ProductBranch)
            .where(and_(ProductBranch.product_id == product_id, ProductBranch.branch_id == branch_id))
            .with_for_update()
        )
        product_branch = result.scalar_one_or_none()
        if not product_branch:
            product_branch = ProductBranch(product_id=product_id, branch_id=branch_id, stock=0)
            self.db.add(product_branch)
            await self.db.flush()
        return product_branch

    async def available(self, tenant_id: int, product_id: int, branch_id: int) -> int:
        return (await self._product_branch(product_id, branch_id)).stock

    async def move(
        self,
        tenant_id: int,
        user_id: int,
        transfer_id: int,
        from_branch_id: int,
        to_branch_id: int,
        item: TransferItem,
    ) -> None:
        source = await self._product_branch(item.product_id, from_branch_id)
        stock_before_source = source.stock
        source.stock -= item.quantity

        dest = await self._product_branch(item.product_id, to_branch_id)
        stock_before_dest = dest.stock
        dest.stock += item.quantity

        for branch_id, quantity, before, after, note in (
            (from_branch_id, -item.quantity, stock_before_source, source.stock,
             f"Salida por traslado a sucursal {to_branch_id}"),
            (to_branch_id, item.quantity, stock_before_dest, dest.stock,
             f"Entrada por traslado desde sucursal {from_branch_id}"),
        ):
            self.db.add(
                InventoryMovement(
                    tenant_id=tenant_id,
                    product_id=item.product_id,
                    user_id=user_id,
                    branch_id=branch_id,
                    batch_id=item.batch_id,
                    movement_type=MovementType.TRANSFER,
                    quantity=quantity,
                    stock_before=before,
                    stock_after=after,
                    reference=f"TR-{transfer_id}",
                    notes=note,
                )
            )

    async def receive(
        self,
        tenant_id: int,
        user_id: int,
        product_id: int,
        branch_id: int,
        quantity: int,
        unit_cost: Decimal,
        reference: str,
        notes: str,
    ) -> None:
        ledger = SqlAlchemyBranchLedger(self.db)
        if not await ledger.open_position(tenant_id, product_id, branch_id):
            raise ProductNotFoundError(product_id)
        await ledger.post(
            tenant_id, user_id, product_id, branch_id, quantity, "entry", unit_cost, reference, notes
        )

    async def set_product_cost(self, tenant_id: int, product_id: int, cost: Decimal) -> None:
        result = await self.db.execute(
            select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
        )
        product = result.scalar_one_or_none()
        if product:
            product.cost = cost
