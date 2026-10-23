from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProductRef:
    id: int
    sku: str
    barcode: str | None


@dataclass(frozen=True)
class CreateProductCommand:
    tenant_id: int
    user_id: int
    attributes: dict[str, Any]


@dataclass(frozen=True)
class UpdateProductCommand:
    tenant_id: int
    user_id: int
    product_id: int
    attributes: dict[str, Any]


@dataclass(frozen=True)
class DeleteProductCommand:
    tenant_id: int
    user_id: int
    product_id: int


@dataclass(frozen=True)
class ImportProductsCommand:
    tenant_id: int
    user_id: int
    rows: tuple[Any, ...]


@dataclass
class ImportResult:
    created: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
