from decimal import Decimal
from typing import Protocol

from app.application.sales.cash_dto import CashSessionSnapshot, CreditSnapshot


class CashSessionStore(Protocol):
    async def get_active(self, tenant_id: int, user_id: int) -> CashSessionSnapshot | None: ...

    async def open(
        self, tenant_id: int, user_id: int, opening_balance: Decimal, notes: str | None
    ) -> int: ...

    async def cash_sales_total(self, session_id: int) -> Decimal: ...

    async def expenses_total(self, session_id: int) -> Decimal: ...

    async def close(self, session_id: int, expected: Decimal, closing: Decimal) -> None: ...


class CreditPaymentStore(Protocol):
    async def get_credit(self, tenant_id: int, credit_id: int) -> CreditSnapshot | None: ...

    async def register(
        self,
        tenant_id: int,
        credit_id: int,
        customer_id: int,
        amount: Decimal,
        new_remaining: Decimal,
        payment_method: str,
        notes: str | None,
    ) -> int: ...


class LoyaltyAdmin(Protocol):
    async def update_config(self, tenant_id: int, changes: dict) -> None: ...

    async def customer_points(self, tenant_id: int, customer_id: int) -> int | None: ...

    async def adjust_points(
        self, tenant_id: int, customer_id: int, delta: int, description: str | None, sale_id: int | None
    ) -> int: ...
