from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SaleLine:
    product_id: int
    quantity: int
    unit_price: Decimal
    batch_id: int | None = None


@dataclass(frozen=True)
class CreateSaleCommand:
    tenant_id: int
    user_id: int
    lines: tuple[SaleLine, ...]
    payment_method: str = "cash"
    notes: str | None = None
    customer_id: int | None = None
    redeemed_points: int = 0
    branch_id: int | None = None  # None: sucursal del vendedor o principal


@dataclass(frozen=True)
class AnnulSaleCommand:
    sale_id: int
    tenant_id: int
    user_id: int


@dataclass(frozen=True)
class ProductStock:
    id: int
    name: str
    stock: int


@dataclass(frozen=True)
class BatchStock:
    id: int
    number: str
    quantity: int


@dataclass(frozen=True)
class LoyaltyProgram:
    points_per_amount: Decimal
    amount_per_point: Decimal
    min_redemption_points: int


@dataclass(frozen=True)
class SoldItem:
    product_id: int
    quantity: int
    batch_id: int | None


@dataclass(frozen=True)
class SaleSnapshot:
    id: int
    status: str
    items: tuple[SoldItem, ...]
    branch_id: int | None = None
