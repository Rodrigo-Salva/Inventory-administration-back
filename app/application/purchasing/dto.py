from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class PurchaseItemInput:
    product_id: int
    quantity: int
    unit_cost: Decimal


@dataclass(frozen=True)
class CreatePurchaseCommand:
    tenant_id: int
    user_id: int
    supplier_id: int
    branch_id: int
    items: tuple[PurchaseItemInput, ...]
    reference_number: str | None = None
    notes: str | None = None
    due_date: datetime | None = None


@dataclass(frozen=True)
class PurchaseActionCommand:
    purchase_id: int
    tenant_id: int
    user_id: int


@dataclass(frozen=True)
class PurchaseSnapshot:
    id: int
    status: str
    branch_id: int
    reference_number: str | None
    items: tuple[PurchaseItemInput, ...]
