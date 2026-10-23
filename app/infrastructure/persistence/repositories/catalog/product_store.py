from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog.dto import ProductRef
from app.domain.catalog.errors import ProductConflictError
from app.infrastructure.persistence.repositories.catalog.product_repo import ProductRepository
from app.infrastructure.persistence.repositories.inventory.branch_ledger import SqlAlchemyBranchLedger
from app.infrastructure.persistence.repositories.inventory.branch_resolver import SqlAlchemyBranchResolver


class SqlAlchemyProductStore:
    """Adaptador SQLAlchemy del puerto ProductStore (reutiliza ProductRepository)."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductRepository(db)
        self.ledger = SqlAlchemyBranchLedger(db)
        self.branches = SqlAlchemyBranchResolver(db)

    @staticmethod
    def _ref(product) -> ProductRef | None:
        return ProductRef(product.id, product.sku, product.barcode) if product else None

    async def get(self, tenant_id: int, product_id: int) -> ProductRef | None:
        return self._ref(await self.repo.get_by_id(product_id, tenant_id))

    async def find_by_sku(self, tenant_id: int, sku: str) -> ProductRef | None:
        return self._ref(await self.repo.get_by_sku(sku, tenant_id))

    async def find_by_barcode(self, tenant_id: int, barcode: str) -> ProductRef | None:
        return self._ref(await self.repo.get_by_barcode(barcode, tenant_id))

    async def create(self, tenant_id: int, user_id: int, attributes: dict[str, Any]) -> int:
        initial_stock = int(attributes.get("stock") or 0)
        try:
            # savepoint: un conflicto de unicidad no invalida el resto de la transacción
            async with self.db.begin_nested():
                product = await self.repo.create({**attributes, "stock": 0}, user_id=user_id)
        except IntegrityError as error:
            raise ProductConflictError() from error
        if initial_stock > 0:
            # el stock inicial entra a una sucursal con su movimiento INITIAL (products.stock = suma de sucursales)
            branch_id = await self.branches.resolve(tenant_id, user_id)
            await self.ledger.open_position(tenant_id, product.id, branch_id)
            await self.ledger.post(
                tenant_id, user_id, product.id, branch_id, initial_stock, "initial",
                reference="STOCK-INICIAL", notes="Stock inicial al crear el producto",
            )
        return product.id

    async def update(
        self, tenant_id: int, user_id: int, product_id: int, attributes: dict[str, Any]
    ) -> None:
        try:
            async with self.db.begin_nested():
                await self.repo.update(product_id, attributes, tenant_id, user_id=user_id)
        except IntegrityError as error:
            raise ProductConflictError() from error

    async def soft_delete(self, tenant_id: int, user_id: int, product_id: int) -> bool:
        return await self.repo.delete(product_id, tenant_id, user_id=user_id)
