from decimal import Decimal
from typing import Protocol

from app.application.purchasing.dto import CreatePurchaseCommand, PurchaseSnapshot


class PurchaseStore(Protocol):
    async def create(self, command: CreatePurchaseCommand, total: Decimal) -> int: ...

    async def get(self, tenant_id: int, purchase_id: int) -> PurchaseSnapshot | None: ...

    async def mark_received(self, purchase_id: int) -> None: ...

    async def mark_cancelled(self, purchase_id: int) -> None: ...


class StockReceiptPort(Protocol):
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
    ) -> None: ...

    async def set_product_cost(self, tenant_id: int, product_id: int, cost: Decimal) -> None: ...
