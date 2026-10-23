from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class CustomerRef:
    id: int
    document_number: str | None
    credit_limit: Decimal
    current_balance: Decimal


@dataclass(frozen=True)
class CreateCustomerCommand:
    tenant_id: int
    attributes: dict[str, Any]
    can_manage_credit: bool = False


@dataclass(frozen=True)
class UpdateCustomerCommand:
    tenant_id: int
    customer_id: int
    changes: dict[str, Any] = field(default_factory=dict)
    can_manage_credit: bool = False


@dataclass(frozen=True)
class DeleteCustomerCommand:
    tenant_id: int
    customer_id: int


@dataclass(frozen=True)
class QuoteLine:
    product_id: int
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class CreateQuoteCommand:
    tenant_id: int
    user_id: int
    valid_until: date
    lines: tuple[QuoteLine, ...]
    customer_id: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ConvertQuoteCommand:
    tenant_id: int
    user_id: int
    quote_id: int
    payment_method: str = "cash"


@dataclass(frozen=True)
class QuoteSnapshot:
    id: int
    status: str
    customer_id: int | None
    notes: str | None
    lines: tuple[QuoteLine, ...]
