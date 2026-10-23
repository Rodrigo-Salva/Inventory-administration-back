from dataclasses import dataclass


@dataclass(frozen=True)
class StockProduct:
    id: int
    name: str
    stock: int


@dataclass(frozen=True)
class CreateAdjustmentCommand:
    tenant_id: int
    user_id: int
    product_id: int
    adjustment_type: str
    quantity: float
    reason: str
    notes: str | None = None
    branch_id: int | None = None  # None: sucursal del usuario o principal


@dataclass(frozen=True)
class TransferItem:
    product_id: int
    quantity: int
    batch_id: int | None = None


@dataclass(frozen=True)
class CreateTransferCommand:
    tenant_id: int
    user_id: int
    from_branch_id: int
    to_branch_id: int
    items: tuple[TransferItem, ...]
    notes: str | None = None
    reference: str | None = None
    complete_now: bool = False


@dataclass(frozen=True)
class TransferActionCommand:
    transfer_id: int
    tenant_id: int


@dataclass(frozen=True)
class TransferSnapshot:
    id: int
    user_id: int
    status: str
    from_branch_id: int
    to_branch_id: int
    items: tuple[TransferItem, ...]


@dataclass(frozen=True)
class StockPosition:
    """Estado de un producto en una sucursal, ya bloqueado para modificar."""

    product_id: int
    name: str
    stock: int


@dataclass(frozen=True)
class AddStockCommand:
    tenant_id: int
    user_id: int
    product_id: int
    branch_id: int
    quantity: int
    unit_cost: object = None
    reference: str | None = None
    notes: str | None = None
    aisle: str | None = None
    shelf: str | None = None
    bin: str | None = None


@dataclass(frozen=True)
class RemoveStockCommand:
    tenant_id: int
    user_id: int
    product_id: int
    branch_id: int
    quantity: int
    reference: str | None = None
    notes: str | None = None
    aisle: str | None = None
    shelf: str | None = None
    bin: str | None = None


@dataclass(frozen=True)
class AdjustStockToCommand:
    tenant_id: int
    user_id: int
    product_id: int
    branch_id: int
    new_stock: int
    reason: str | None = None


@dataclass(frozen=True)
class StartAuditCommand:
    tenant_id: int
    user_id: int
    branch_id: int
    notes: str | None = None


@dataclass(frozen=True)
class CountAuditItemCommand:
    tenant_id: int
    audit_id: int
    product_id: int
    counted_stock: int
    notes: str | None = None


@dataclass(frozen=True)
class CompleteAuditCommand:
    tenant_id: int
    user_id: int
    audit_id: int


@dataclass(frozen=True)
class AuditItemSnapshot:
    id: int
    product_id: int
    counted_stock: int
    difference: int
    is_adjusted: bool


@dataclass(frozen=True)
class AuditSnapshot:
    id: int
    branch_id: int
    status: str
    items: tuple[AuditItemSnapshot, ...]
