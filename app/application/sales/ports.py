from decimal import Decimal
from typing import Protocol

from app.application.sales.dto import (
    BatchStock,
    LoyaltyProgram,
    ProductStock,
    SaleLine,
    SaleSnapshot,
)


class SaleStore(Protocol):
    async def create(
        self,
        tenant_id: int,
        user_id: int,
        payment_method: str,
        notes: str | None,
        cash_session_id: int | None = None,
        branch_id: int | None = None,
    ) -> int: ...

    async def add_item(self, sale_id: int, line: SaleLine, subtotal: Decimal) -> None: ...

    async def finalize(
        self,
        sale_id: int,
        total: Decimal,
        customer_id: int | None,
        redeemed_points: int,
        points_discount: Decimal,
    ) -> None: ...

    async def get_for_annulment(self, sale_id: int, tenant_id: int) -> SaleSnapshot | None: ...

    async def mark_annulled(self, sale_id: int) -> None: ...


class InventoryPort(Protocol):
    async def get_product(
        self, tenant_id: int, product_id: int, branch_id: int | None = None
    ) -> ProductStock | None:
        """Producto con el stock DE LA SUCURSAL (bloqueado para modificarlo)."""
        ...

    async def get_batch(self, tenant_id: int, batch_id: int) -> BatchStock | None: ...

    async def register_sale_exit(
        self,
        tenant_id: int,
        user_id: int,
        sale_id: int,
        product_id: int,
        batch_id: int | None,
        quantity: int,
        branch_id: int | None = None,
    ) -> None: ...

    async def register_annulment_entry(
        self,
        tenant_id: int,
        user_id: int,
        sale_id: int,
        product_id: int,
        batch_id: int | None,
        quantity: int,
        branch_id: int | None = None,
    ) -> None: ...


class LoyaltyPort(Protocol):
    async def get_active_program(self, tenant_id: int) -> LoyaltyProgram | None: ...

    async def get_points(self, tenant_id: int, customer_id: int) -> int | None: ...

    async def redeem(self, tenant_id: int, customer_id: int, sale_id: int, points: int) -> None: ...

    async def earn(self, tenant_id: int, customer_id: int, sale_id: int, points: int) -> None: ...

    async def reverse_for_sale(self, tenant_id: int, sale_id: int) -> None: ...


class CreditPort(Protocol):
    async def has_available_credit(
        self, tenant_id: int, customer_id: int, amount: Decimal
    ) -> bool: ...

    async def open_credit(
        self, tenant_id: int, customer_id: int, sale_id: int, amount: Decimal
    ) -> None: ...

    async def annul_for_sale(self, tenant_id: int, sale_id: int) -> None: ...
