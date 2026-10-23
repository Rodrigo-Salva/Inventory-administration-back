from datetime import date
from typing import Any, Protocol

from app.application.catalog.admin_dto import BranchRef, CategoryRef, SupplierRef


class CategoryStore(Protocol):
    async def get(self, tenant_id: int, category_id: int) -> CategoryRef | None: ...

    async def find_by_code(self, tenant_id: int, code: str) -> CategoryRef | None: ...

    async def children_count(self, tenant_id: int, category_id: int) -> int: ...

    async def parent_of(self, tenant_id: int, category_id: int) -> int | None: ...

    async def create(self, tenant_id: int, attributes: dict[str, Any]) -> int: ...

    async def update(self, tenant_id: int, category_id: int, changes: dict[str, Any]) -> None: ...

    async def soft_delete(self, tenant_id: int, category_id: int) -> None: ...


class SupplierStore(Protocol):
    async def get(self, tenant_id: int, supplier_id: int) -> SupplierRef | None: ...

    async def find_by_code(self, tenant_id: int, code: str) -> SupplierRef | None: ...

    async def create(self, tenant_id: int, attributes: dict[str, Any]) -> int: ...

    async def update(self, tenant_id: int, supplier_id: int, changes: dict[str, Any]) -> None: ...

    async def soft_delete(self, tenant_id: int, supplier_id: int) -> None: ...


class BranchStore(Protocol):
    async def get(self, tenant_id: int, branch_id: int) -> BranchRef | None: ...

    async def create(self, tenant_id: int, user_id: int | None, attributes: dict[str, Any]) -> int: ...

    async def update(
        self, tenant_id: int, user_id: int | None, branch_id: int, changes: dict[str, Any]
    ) -> None: ...

    async def soft_delete(self, tenant_id: int, user_id: int | None, branch_id: int) -> None: ...


class BatchStore(Protocol):
    async def create(
        self,
        tenant_id: int,
        product_id: int,
        batch_number: str,
        expiration_date: date,
        initial_quantity: int,
        is_active: bool,
    ) -> int:
        """Crea solo el lote; el ingreso de stock lo registra el caso de uso en una sucursal."""
        ...
