from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.application.inventory.picking import PickingLine
from app.infrastructure.persistence.models.inventory.inventory_movement import InventoryMovement
from app.infrastructure.persistence.models.inventory.product_branch import ProductBranch
from app.infrastructure.persistence.models.sales.sale import Sale, SaleItem


class SqlAlchemyPickingReader:
    """Adaptador SQLAlchemy del puerto PickingReader."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _branch_of(self, sale: Sale, tenant_id: int) -> int | None:
        if sale.user and sale.user.branch_id:
            return sale.user.branch_id
        # respaldo: sucursal donde se registró el movimiento de la venta
        result = await self.db.execute(
            select(InventoryMovement.branch_id)
            .where(InventoryMovement.reference == f"VENTA #{sale.id}", InventoryMovement.tenant_id == tenant_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def lines_for_sale(self, tenant_id: int, sale_id: int) -> list[PickingLine] | None:
        result = await self.db.execute(
            select(Sale)
            .options(joinedload(Sale.items).joinedload(SaleItem.product), joinedload(Sale.user))
            .where(and_(Sale.id == sale_id, Sale.tenant_id == tenant_id))
        )
        sale = result.unique().scalar_one_or_none()
        if not sale:
            return None
        branch_id = await self._branch_of(sale, tenant_id)

        lines = []
        for item in sale.items:
            position = (
                await self.db.execute(
                    select(ProductBranch).where(
                        ProductBranch.product_id == item.product_id, ProductBranch.branch_id == branch_id
                    )
                )
            ).scalar_one_or_none()
            lines.append(
                PickingLine(
                    item_id=item.id, product_id=item.product_id, product_name=item.product.name,
                    sku=item.product.sku, quantity=item.quantity,
                    aisle=position.aisle if position else None,
                    shelf=position.shelf if position else None,
                    bin=position.bin if position else None,
                )
            )
        return lines
