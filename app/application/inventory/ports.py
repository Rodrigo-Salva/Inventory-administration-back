from typing import Protocol

from app.application.inventory.dto import (
    AuditSnapshot,
    CreateAdjustmentCommand,
    CreateTransferCommand,
    StartAuditCommand,
    StockPosition,
    StockProduct,
    TransferItem,
    TransferSnapshot,
)


class AdjustmentStore(Protocol):
    async def lock_product(
        self, tenant_id: int, product_id: int, branch_id: int | None = None
    ) -> StockProduct | None:
        """Producto con el stock DE LA SUCURSAL, bloqueado para modificarlo."""
        ...

    async def record(
        self, command: CreateAdjustmentCommand, delta: int, stock_before: int, branch_id: int | None = None
    ) -> int: ...


class TransferStore(Protocol):
    async def create(self, command: CreateTransferCommand) -> int: ...

    async def get(self, tenant_id: int, transfer_id: int) -> TransferSnapshot | None: ...

    async def mark_completed(self, transfer_id: int) -> None: ...

    async def mark_cancelled(self, transfer_id: int) -> None: ...


class BranchStockPort(Protocol):
    async def available(self, tenant_id: int, product_id: int, branch_id: int) -> int: ...

    async def move(
        self,
        tenant_id: int,
        user_id: int,
        transfer_id: int,
        from_branch_id: int,
        to_branch_id: int,
        item: TransferItem,
    ) -> None: ...


class BranchLedger(Protocol):
    """Libro de stock por sucursal: abre una posición bloqueada y registra movimientos."""

    async def open_position(
        self,
        tenant_id: int,
        product_id: int,
        branch_id: int,
        aisle: str | None = None,
        shelf: str | None = None,
        bin: str | None = None,
    ) -> StockPosition | None: ...

    async def current_stock(self, tenant_id: int, product_id: int, branch_id: int) -> int: ...

    async def post(
        self,
        tenant_id: int,
        user_id: int,
        product_id: int,
        branch_id: int,
        delta: int,
        movement_type: str,
        unit_cost: object = None,
        reference: str | None = None,
        notes: str | None = None,
        batch_id: int | None = None,
    ) -> int: ...


class AuditStore(Protocol):
    async def create(self, command: StartAuditCommand) -> int: ...

    async def get(self, tenant_id: int, audit_id: int) -> AuditSnapshot | None: ...

    async def upsert_item(
        self, audit_id: int, product_id: int, expected: int, counted: int, notes: str | None
    ) -> int: ...

    async def mark_item_adjusted(self, item_id: int) -> None: ...

    async def complete(self, audit_id: int) -> None: ...
