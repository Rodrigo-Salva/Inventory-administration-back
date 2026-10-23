from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.catalog.category import Category
from app.infrastructure.persistence.models.catalog.product import Product
from app.infrastructure.persistence.models.catalog.supplier import Supplier
from app.infrastructure.persistence.models.inventory.branch import Branch
from app.infrastructure.persistence.models.sales.customer import Customer


class SqlAlchemyTenantResources:
    """Comprueba que productos, sucursales y proveedores pertenezcan al tenant."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def missing_products(self, tenant_id: int, product_ids: set[int]) -> set[int]:
        result = await self.db.execute(
            select(Product.id).where(Product.tenant_id == tenant_id, Product.id.in_(product_ids))
        )
        return product_ids - set(result.scalars().all())

    async def branch_exists(self, tenant_id: int, branch_id: int) -> bool:
        result = await self.db.execute(
            select(Branch.id).where(
                Branch.id == branch_id, Branch.tenant_id == tenant_id, Branch.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none() is not None

    async def supplier_exists(self, tenant_id: int, supplier_id: int) -> bool:
        result = await self.db.execute(
            select(Supplier.id).where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none() is not None

    async def category_exists(self, tenant_id: int, category_id: int) -> bool:
        result = await self.db.execute(
            select(Category.id).where(Category.id == category_id, Category.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none() is not None

    async def customer_exists(self, tenant_id: int, customer_id: int) -> bool:
        result = await self.db.execute(
            select(Customer.id).where(
                Customer.id == customer_id, Customer.tenant_id == tenant_id, Customer.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none() is not None
