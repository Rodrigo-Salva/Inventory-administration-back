from app.application.inventory.dto import (
    AddStockCommand,
    AdjustStockToCommand,
    CompleteAuditCommand,
    CountAuditItemCommand,
    RemoveStockCommand,
    StartAuditCommand,
)
from app.application.inventory.ports import AuditStore, BranchLedger
from app.application.shared.ports import TenantResources, UnitOfWork
from app.domain.inventory.errors import (
    BranchNotFoundError,
    InsufficientStockError,
    InvalidAuditError,
    InvalidStockOperationError,
    ProductNotFoundError,
)

ENTRY, EXIT, ADJUSTMENT = "entry", "exit", "adjustment"
AUDIT_IN_PROGRESS = "in_progress"


class _LedgerUseCase:
    def __init__(self, ledger: BranchLedger, resources: TenantResources, uow: UnitOfWork):
        self.ledger = ledger
        self.resources = resources
        self.uow = uow

    async def _open(self, cmd, aisle=None, shelf=None, bin=None):
        if not await self.resources.branch_exists(cmd.tenant_id, cmd.branch_id):
            raise BranchNotFoundError()
        position = await self.ledger.open_position(
            cmd.tenant_id, cmd.product_id, cmd.branch_id, aisle, shelf, bin
        )
        if not position:
            raise ProductNotFoundError(cmd.product_id)
        return position


class AddStock(_LedgerUseCase):
    async def execute(self, cmd: AddStockCommand) -> int:
        try:
            if cmd.quantity <= 0:
                raise InvalidStockOperationError("La cantidad debe ser mayor a 0")
            await self._open(cmd, cmd.aisle, cmd.shelf, cmd.bin)
            movement_id = await self.ledger.post(
                cmd.tenant_id, cmd.user_id, cmd.product_id, cmd.branch_id,
                cmd.quantity, ENTRY, cmd.unit_cost, cmd.reference, cmd.notes,
            )
            await self.uow.commit()
            return movement_id
        except Exception:
            await self.uow.rollback()
            raise


class RemoveStock(_LedgerUseCase):
    async def execute(self, cmd: RemoveStockCommand) -> int:
        try:
            if cmd.quantity <= 0:
                raise InvalidStockOperationError("La cantidad debe ser mayor a 0")
            position = await self._open(cmd, cmd.aisle, cmd.shelf, cmd.bin)
            if position.stock < cmd.quantity:
                raise InsufficientStockError(position.name, cmd.quantity, position.stock)
            movement_id = await self.ledger.post(
                cmd.tenant_id, cmd.user_id, cmd.product_id, cmd.branch_id,
                -cmd.quantity, EXIT, None, cmd.reference, cmd.notes,
            )
            await self.uow.commit()
            return movement_id
        except Exception:
            await self.uow.rollback()
            raise


class AdjustStockTo(_LedgerUseCase):
    """Fija el stock de una sucursal en un valor exacto (conteo físico)."""

    async def execute(self, cmd: AdjustStockToCommand) -> int:
        try:
            movement_id = await self._adjust(cmd)
            await self.uow.commit()
            return movement_id
        except Exception:
            await self.uow.rollback()
            raise

    async def _adjust(self, cmd: AdjustStockToCommand) -> int:
        if cmd.new_stock < 0:
            raise InvalidStockOperationError("El stock no puede ser negativo")
        position = await self._open(cmd)
        difference = cmd.new_stock - position.stock
        if difference == 0:
            raise InvalidStockOperationError("El nuevo stock es igual al actual en esta sucursal")
        notes = f"Ajuste de inventario: {cmd.reason}" if cmd.reason else "Ajuste de inventario"
        return await self.ledger.post(
            cmd.tenant_id, cmd.user_id, cmd.product_id, cmd.branch_id,
            difference, ADJUSTMENT, None, None, notes,
        )


class StartAudit:
    def __init__(self, audits: AuditStore, resources: TenantResources, uow: UnitOfWork):
        self.audits = audits
        self.resources = resources
        self.uow = uow

    async def execute(self, cmd: StartAuditCommand) -> int:
        try:
            if not await self.resources.branch_exists(cmd.tenant_id, cmd.branch_id):
                raise BranchNotFoundError()
            audit_id = await self.audits.create(cmd)
            await self.uow.commit()
            return audit_id
        except Exception:
            await self.uow.rollback()
            raise


class CountAuditItem:
    def __init__(
        self, audits: AuditStore, ledger: BranchLedger, resources: TenantResources, uow: UnitOfWork
    ):
        self.audits = audits
        self.ledger = ledger
        self.resources = resources
        self.uow = uow

    async def execute(self, cmd: CountAuditItemCommand) -> int:
        try:
            audit = await self.audits.get(cmd.tenant_id, cmd.audit_id)
            if not audit or audit.status != AUDIT_IN_PROGRESS:
                raise InvalidAuditError("Auditoría no encontrada o ya finalizada")
            if await self.resources.missing_products(cmd.tenant_id, {cmd.product_id}):
                raise ProductNotFoundError(cmd.product_id)
            expected = await self.ledger.current_stock(cmd.tenant_id, cmd.product_id, audit.branch_id)
            item_id = await self.audits.upsert_item(
                audit.id, cmd.product_id, expected, cmd.counted_stock, cmd.notes
            )
            await self.uow.commit()
            return item_id
        except Exception:
            await self.uow.rollback()
            raise


class CompleteAudit:
    """Cierra la auditoría y ajusta, de forma atómica, cada diferencia contada."""

    def __init__(
        self, audits: AuditStore, ledger: BranchLedger, resources: TenantResources, uow: UnitOfWork
    ):
        self.audits = audits
        self.ledger = ledger
        self.adjust = AdjustStockTo(ledger, resources, uow)
        self.uow = uow

    async def execute(self, cmd: CompleteAuditCommand) -> int:
        try:
            audit = await self.audits.get(cmd.tenant_id, cmd.audit_id)
            if not audit or audit.status != AUDIT_IN_PROGRESS:
                raise InvalidAuditError("Auditoría no encontrada o ya finalizada")
            for item in audit.items:
                if item.is_adjusted or item.difference == 0:
                    continue
                current = await self.ledger.current_stock(cmd.tenant_id, item.product_id, audit.branch_id)
                if current != item.counted_stock:  # si ya coincide, no hay nada que ajustar
                    await self.adjust._adjust(
                        AdjustStockToCommand(
                            cmd.tenant_id, cmd.user_id, item.product_id, audit.branch_id,
                            item.counted_stock, f"Ajuste por Auditoría #{audit.id}",
                        )
                    )
                await self.audits.mark_item_adjusted(item.id)
            await self.audits.complete(audit.id)
            await self.uow.commit()
            return audit.id
        except Exception:
            await self.uow.rollback()
            raise
