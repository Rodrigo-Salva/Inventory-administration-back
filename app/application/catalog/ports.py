from typing import Any, Protocol

from app.application.catalog.dto import ProductRef


class ProductStore(Protocol):
    async def get(self, tenant_id: int, product_id: int) -> ProductRef | None: ...

    async def find_by_sku(self, tenant_id: int, sku: str) -> ProductRef | None: ...

    async def find_by_barcode(self, tenant_id: int, barcode: str) -> ProductRef | None: ...

    async def create(self, tenant_id: int, user_id: int, attributes: dict[str, Any]) -> int:
        """Crea el producto aislado en un savepoint; lanza ProductConflictError si choca."""
        ...

    async def update(
        self, tenant_id: int, user_id: int, product_id: int, attributes: dict[str, Any]
    ) -> None: ...

    async def soft_delete(self, tenant_id: int, user_id: int, product_id: int) -> bool: ...
