from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.dto import BatchStock, ProductStock
from app.application.shared.ports import TaskScheduler
from app.infrastructure.persistence.models.catalog.product_batch import ProductBatch
from app.infrastructure.persistence.repositories.inventory.branch_ledger import SqlAlchemyBranchLedger
from app.infrastructure.persistence.repositories.inventory.branch_resolver import SqlAlchemyBranchResolver


class SqlAlchemyInventory:
    """Adaptador SQLAlchemy del puerto InventoryPort de ventas.

    El stock real vive por sucursal: cada movimiento pasa por el libro de la sucursal
    (`BranchLedger`), que mantiene `products.stock` como la suma de sus sucursales, registra
    el kardex y gestiona las alertas. Las lecturas bloquean la fila (`FOR UPDATE`) para
    evitar sobreventa cuando dos ventas concurrentes descuentan el mismo producto.
    """

    def __init__(self, db: AsyncSession, scheduler: TaskScheduler | None = None):
        self.db = db
        self.ledger = SqlAlchemyBranchLedger(db, scheduler)
        self.branches = SqlAlchemyBranchResolver(db)

    async def _batch(self, tenant_id: int, batch_id: int) -> ProductBatch | None:
        query = select(ProductBatch).where(ProductBatch.id == batch_id, ProductBatch.tenant_id == tenant_id)
        return (await self.db.execute(query.with_for_update())).scalar_one_or_none()

    async def _branch(self, tenant_id: int, user_id: int | None, branch_id: int | None) -> int:
        return branch_id if branch_id is not None else await self.branches.resolve(tenant_id, user_id)

    async def get_product(self, tenant_id: int, product_id: int, branch_id: int | None = None) -> ProductStock | None:
        branch_id = await self._branch(tenant_id, None, branch_id)
        position = await self.ledger.open_position(tenant_id, product_id, branch_id)
        return ProductStock(position.product_id, position.name, position.stock) if position else None

    async def get_batch(self, tenant_id: int, batch_id: int) -> BatchStock | None:
        batch = await self._batch(tenant_id, batch_id)
        return BatchStock(batch.id, batch.batch_number, batch.current_quantity) if batch else None

    async def register_sale_exit(
        self,
        tenant_id: int,
        user_id: int,
        sale_id: int,
        product_id: int,
        batch_id: int | None,
        quantity: int,
        branch_id: int | None = None,
    ) -> None:
        branch_id = await self._branch(tenant_id, user_id, branch_id)
        if batch_id:
            (await self._batch(tenant_id, batch_id)).current_quantity -= quantity
        await self.ledger.post(
            tenant_id, user_id, product_id, branch_id, -quantity, "exit",
            reference=f"VENTA #{sale_id}", notes="Venta realizada por el POS", batch_id=batch_id,
        )

    async def register_annulment_entry(
        self,
        tenant_id: int,
        user_id: int,
        sale_id: int,
        product_id: int,
        batch_id: int | None,
        quantity: int,
        branch_id: int | None = None,
    ) -> None:
        branch_id = await self._branch(tenant_id, user_id, branch_id)
        if batch_id:
            batch = await self._batch(tenant_id, batch_id)
            if batch:
                batch.current_quantity += quantity
        await self.ledger.open_position(tenant_id, product_id, branch_id)
        await self.ledger.post(
            tenant_id, user_id, product_id, branch_id, quantity, "adjustment",
            reference=f"ANULACIÓN #{sale_id}", notes="Anulación de venta realizada", batch_id=batch_id,
        )
