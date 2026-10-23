from app.application.inventory.dto import (
    CreateAdjustmentCommand,
    CreateTransferCommand,
    TransferActionCommand,
    TransferItem,
)
from app.application.inventory.ports import AdjustmentStore, BranchStockPort, TransferStore
from app.application.shared.ports import BranchResolver, TenantResources, UnitOfWork
from app.domain.inventory import rules
from app.domain.inventory.errors import (
    BranchNotFoundError,
    InsufficientBranchStockError,
    InsufficientStockError,
    InvalidTransferError,
    ProductNotFoundError,
    TransferNotFoundError,
)


class CreateAdjustment:
    """Ajuste manual de stock (merma, pérdida, corrección, uso interno)."""

    def __init__(self, store: AdjustmentStore, uow: UnitOfWork, branches: BranchResolver | None = None):
        self.store = store
        self.uow = uow
        self.branches = branches

    async def execute(self, cmd: CreateAdjustmentCommand) -> int:
        try:
            delta = rules.signed_adjustment(cmd.adjustment_type, cmd.quantity)
            branch_id = (
                await self.branches.resolve(cmd.tenant_id, cmd.user_id, cmd.branch_id)
                if self.branches else cmd.branch_id
            )
            product = await self.store.lock_product(cmd.tenant_id, cmd.product_id, branch_id)
            if not product:
                raise ProductNotFoundError(cmd.product_id)
            if product.stock + delta < 0:
                raise InsufficientStockError(product.name, -delta, product.stock)
            adjustment_id = await self.store.record(cmd, delta, product.stock, branch_id)
            await self.uow.commit()
            return adjustment_id
        except Exception:
            await self.uow.rollback()
            raise


async def _move_all(
    stock: BranchStockPort,
    tenant_id: int,
    user_id: int,
    transfer_id: int,
    from_branch_id: int,
    to_branch_id: int,
    items: tuple[TransferItem, ...],
) -> None:
    for item in items:
        if await stock.available(tenant_id, item.product_id, from_branch_id) < item.quantity:
            raise InsufficientBranchStockError(item.product_id)
        await stock.move(tenant_id, user_id, transfer_id, from_branch_id, to_branch_id, item)


class CreateStockTransfer:
    def __init__(
        self,
        transfers: TransferStore,
        stock: BranchStockPort,
        resources: TenantResources,
        uow: UnitOfWork,
    ):
        self.transfers = transfers
        self.stock = stock
        self.resources = resources
        self.uow = uow

    async def execute(self, cmd: CreateTransferCommand) -> int:
        try:
            await self._validate(cmd)
            transfer_id = await self.transfers.create(cmd)
            if cmd.complete_now:
                await _move_all(
                    self.stock, cmd.tenant_id, cmd.user_id, transfer_id,
                    cmd.from_branch_id, cmd.to_branch_id, cmd.items,
                )
                await self.transfers.mark_completed(transfer_id)
            await self.uow.commit()
            return transfer_id
        except Exception:
            await self.uow.rollback()
            raise

    async def _validate(self, cmd: CreateTransferCommand) -> None:
        if cmd.from_branch_id == cmd.to_branch_id:
            raise InvalidTransferError("La sucursal de origen y destino deben ser distintas")
        if not cmd.items:
            raise InvalidTransferError("El traslado debe tener al menos un ítem")
        for branch_id in (cmd.from_branch_id, cmd.to_branch_id):
            if not await self.resources.branch_exists(cmd.tenant_id, branch_id):
                raise BranchNotFoundError()
        missing = await self.resources.missing_products(
            cmd.tenant_id, {i.product_id for i in cmd.items}
        )
        if missing:
            raise ProductNotFoundError(sorted(missing)[0])


class CompleteStockTransfer:
    def __init__(self, transfers: TransferStore, stock: BranchStockPort, uow: UnitOfWork):
        self.transfers = transfers
        self.stock = stock
        self.uow = uow

    async def execute(self, cmd: TransferActionCommand) -> int:
        try:
            transfer = await self.transfers.get(cmd.tenant_id, cmd.transfer_id)
            if not transfer:
                raise TransferNotFoundError()
            if transfer.status != rules.TRANSFER_PENDING:
                raise InvalidTransferError("Solo se pueden completar traslados en estado pendiente")
            await _move_all(
                self.stock, cmd.tenant_id, transfer.user_id, transfer.id,
                transfer.from_branch_id, transfer.to_branch_id, transfer.items,
            )
            await self.transfers.mark_completed(transfer.id)
            await self.uow.commit()
            return transfer.id
        except Exception:
            await self.uow.rollback()
            raise


class CancelStockTransfer:
    def __init__(self, transfers: TransferStore, uow: UnitOfWork):
        self.transfers = transfers
        self.uow = uow

    async def execute(self, cmd: TransferActionCommand) -> int:
        try:
            transfer = await self.transfers.get(cmd.tenant_id, cmd.transfer_id)
            if not transfer:
                raise TransferNotFoundError()
            if transfer.status != rules.TRANSFER_PENDING:
                raise InvalidTransferError("Solo se pueden cancelar traslados en estado pendiente")
            await self.transfers.mark_cancelled(transfer.id)
            await self.uow.commit()
            return transfer.id
        except Exception:
            await self.uow.rollback()
            raise
