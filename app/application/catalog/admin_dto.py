from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class CategoryRef:
    id: int
    code: str | None
    parent_id: int | None


@dataclass(frozen=True)
class SupplierRef:
    id: int
    code: str
    is_active: bool


@dataclass(frozen=True)
class BranchRef:
    id: int
    stock_units: int


@dataclass(frozen=True)
class CreateEntityCommand:
    tenant_id: int
    attributes: dict[str, Any]
    user_id: int | None = None


@dataclass(frozen=True)
class UpdateEntityCommand:
    tenant_id: int
    entity_id: int
    changes: dict[str, Any] = field(default_factory=dict)
    user_id: int | None = None


@dataclass(frozen=True)
class DeleteEntityCommand:
    tenant_id: int
    entity_id: int
    user_id: int | None = None


@dataclass(frozen=True)
class CreateBatchCommand:
    tenant_id: int
    product_id: int
    batch_number: str
    expiration_date: date
    initial_quantity: int
    is_active: bool = True
    user_id: int | None = None
    branch_id: int | None = None  # sucursal donde ingresa el lote
