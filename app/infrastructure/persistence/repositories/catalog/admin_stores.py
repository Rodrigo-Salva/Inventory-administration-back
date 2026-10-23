from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog.admin_dto import CategoryRef, SupplierRef
from app.domain.catalog.errors import DuplicateCodeError
from app.infrastructure.persistence.models.catalog.category import Category
from app.infrastructure.persistence.models.catalog.product import Product
from app.infrastructure.persistence.models.catalog.product_batch import ProductBatch
from app.infrastructure.persistence.repositories.catalog.category_repo import CategoryRepository
from app.infrastructure.persistence.repositories.catalog.supplier_repo import SupplierRepository


class SqlAlchemyCategoryStore:
    """Adaptador SQLAlchemy del puerto CategoryStore."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CategoryRepository(db)

    @staticmethod
    def _ref(category) -> CategoryRef | None:
        return CategoryRef(category.id, category.code, category.parent_id) if category else None

    async def get(self, tenant_id: int, category_id: int) -> CategoryRef | None:
        return self._ref(await self.repo.get_by_id(category_id, tenant_id))

    async def find_by_code(self, tenant_id: int, code: str) -> CategoryRef | None:
        return self._ref(await self.repo.get_by_code(code, tenant_id))

    async def children_count(self, tenant_id: int, category_id: int) -> int:
        return len(await self.repo.get_children(category_id, tenant_id))

    async def parent_of(self, tenant_id: int, category_id: int) -> int | None:
        result = await self.db.execute(
            select(Category.parent_id).where(Category.id == category_id, Category.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: int, attributes: dict[str, Any]) -> int:
        try:
            async with self.db.begin_nested():
                category = await self.repo.create({**attributes, "tenant_id": tenant_id})
        except IntegrityError as error:
            raise DuplicateCodeError("Ya existe una categoría con ese código") from error
        return category.id

    async def update(self, tenant_id: int, category_id: int, changes: dict[str, Any]) -> None:
        await self.repo.update(category_id, changes, tenant_id)

    async def soft_delete(self, tenant_id: int, category_id: int) -> None:
        await self.repo.delete(category_id, tenant_id)


class SqlAlchemySupplierStore:
    """Adaptador SQLAlchemy del puerto SupplierStore."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SupplierRepository(db)

    @staticmethod
    def _ref(supplier) -> SupplierRef | None:
        return SupplierRef(supplier.id, supplier.code, bool(supplier.is_active)) if supplier else None

    async def get(self, tenant_id: int, supplier_id: int) -> SupplierRef | None:
        return self._ref(await self.repo.get_by_id(supplier_id, tenant_id))

    async def find_by_code(self, tenant_id: int, code: str) -> SupplierRef | None:
        return self._ref(await self.repo.get_by_code(code, tenant_id))

    async def create(self, tenant_id: int, attributes: dict[str, Any]) -> int:
        try:
            async with self.db.begin_nested():
                supplier = await self.repo.create({**attributes, "tenant_id": tenant_id})
        except IntegrityError as error:
            raise DuplicateCodeError("Proveedor con ese código ya existe") from error
        return supplier.id

    async def update(self, tenant_id: int, supplier_id: int, changes: dict[str, Any]) -> None:
        await self.repo.update(supplier_id, changes, tenant_id)

    async def soft_delete(self, tenant_id: int, supplier_id: int) -> None:
        await self.repo.delete(supplier_id, tenant_id)


class SqlAlchemyBatchStore:
    """Adaptador SQLAlchemy del puerto BatchStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        tenant_id: int,
        product_id: int,
        batch_number: str,
        expiration_date: date,
        initial_quantity: int,
        is_active: bool,
    ) -> int:
        batch = ProductBatch(
            tenant_id=tenant_id,
            product_id=product_id,
            batch_number=batch_number,
            expiration_date=expiration_date,
            initial_quantity=initial_quantity,
            current_quantity=initial_quantity,
            is_active=is_active,
        )
        self.db.add(batch)
        await self.db.flush()
        return batch.id
