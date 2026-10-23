"""Composition root de inventario: conecta casos de uso con sus adaptadores."""

from fastapi import BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inventory.dto import (
    AddStockCommand,
    AdjustStockToCommand,
    CompleteAuditCommand,
    CountAuditItemCommand,
    RemoveStockCommand,
    StartAuditCommand,
    CreateAdjustmentCommand,
    CreateTransferCommand,
    TransferActionCommand,
    TransferItem,
)
from app.application.inventory.stock_use_cases import (
    AddStock,
    AdjustStockTo,
    CompleteAudit,
    CountAuditItem,
    RemoveStock,
    StartAudit,
)
from app.application.inventory.use_cases import (
    CancelStockTransfer,
    CompleteStockTransfer,
    CreateAdjustment,
    CreateStockTransfer,
)
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.inventory.adjustment_store import SqlAlchemyAdjustmentStore
from app.infrastructure.persistence.repositories.inventory.audit_store import SqlAlchemyAuditStore
from app.infrastructure.persistence.repositories.inventory.branch_ledger import SqlAlchemyBranchLedger
from app.infrastructure.persistence.repositories.inventory.branch_resolver import SqlAlchemyBranchResolver
from app.infrastructure.persistence.repositories.inventory.branch_stock_gateway import SqlAlchemyBranchStock
from app.infrastructure.persistence.repositories.inventory.transfer_store import SqlAlchemyTransferStore
from app.infrastructure.persistence.tenant_resources import SqlAlchemyTenantResources
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.presentation.schemas.inventory.adjustment import AdjustmentCreate
from app.presentation.schemas.inventory.stock_transfer import StockTransferCreate


def get_create_adjustment(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> CreateAdjustment:
    return CreateAdjustment(
        SqlAlchemyAdjustmentStore(db, background_tasks), SqlAlchemyUnitOfWork(db), SqlAlchemyBranchResolver(db)
    )


def get_create_transfer(db: AsyncSession = Depends(get_db)) -> CreateStockTransfer:
    return CreateStockTransfer(
        SqlAlchemyTransferStore(db),
        SqlAlchemyBranchStock(db),
        SqlAlchemyTenantResources(db),
        SqlAlchemyUnitOfWork(db),
    )


def get_complete_transfer(db: AsyncSession = Depends(get_db)) -> CompleteStockTransfer:
    return CompleteStockTransfer(
        SqlAlchemyTransferStore(db), SqlAlchemyBranchStock(db), SqlAlchemyUnitOfWork(db)
    )


def get_cancel_transfer(db: AsyncSession = Depends(get_db)) -> CancelStockTransfer:
    return CancelStockTransfer(SqlAlchemyTransferStore(db), SqlAlchemyUnitOfWork(db))


def to_adjustment_command(payload: AdjustmentCreate, tenant_id: int, user_id: int) -> CreateAdjustmentCommand:
    return CreateAdjustmentCommand(
        tenant_id=tenant_id,
        user_id=user_id,
        product_id=payload.product_id,
        adjustment_type=payload.adjustment_type,
        quantity=payload.quantity,
        reason=getattr(payload.reason, "value", payload.reason),
        notes=payload.notes,
        branch_id=payload.branch_id,
    )


def to_transfer_command(payload: StockTransferCreate, tenant_id: int, user_id: int) -> CreateTransferCommand:
    status = getattr(payload.status, "value", payload.status)
    return CreateTransferCommand(
        tenant_id=tenant_id,
        user_id=user_id,
        from_branch_id=payload.from_branch_id,
        to_branch_id=payload.to_branch_id,
        items=tuple(TransferItem(i.product_id, i.quantity, i.batch_id) for i in payload.items),
        notes=payload.notes,
        reference=payload.reference,
        complete_now=status == "completed",
    )


def to_transfer_action(transfer_id: int, tenant_id: int) -> TransferActionCommand:
    return TransferActionCommand(transfer_id=transfer_id, tenant_id=tenant_id)


def get_add_stock(db: AsyncSession = Depends(get_db)) -> AddStock:
    return AddStock(SqlAlchemyBranchLedger(db), SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db))


def get_remove_stock(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> RemoveStock:
    return RemoveStock(
        SqlAlchemyBranchLedger(db, background_tasks), SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db)
    )


def get_adjust_stock(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> AdjustStockTo:
    return AdjustStockTo(
        SqlAlchemyBranchLedger(db, background_tasks), SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db)
    )


def get_start_audit(db: AsyncSession = Depends(get_db)) -> StartAudit:
    return StartAudit(SqlAlchemyAuditStore(db), SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db))


def get_count_audit_item(db: AsyncSession = Depends(get_db)) -> CountAuditItem:
    return CountAuditItem(
        SqlAlchemyAuditStore(db), SqlAlchemyBranchLedger(db),
        SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db),
    )


def get_complete_audit(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> CompleteAudit:
    return CompleteAudit(
        SqlAlchemyAuditStore(db), SqlAlchemyBranchLedger(db, background_tasks),
        SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db),
    )


def to_add_stock(r, tenant_id: int, user_id: int) -> AddStockCommand:
    return AddStockCommand(
        tenant_id, user_id, r.product_id, r.branch_id, r.quantity, r.unit_cost,
        r.reference, r.notes, r.aisle, r.shelf, r.bin,
    )


def to_remove_stock(r, tenant_id: int, user_id: int) -> RemoveStockCommand:
    return RemoveStockCommand(
        tenant_id, user_id, r.product_id, r.branch_id, r.quantity,
        r.reference, r.notes, r.aisle, r.shelf, r.bin,
    )


def to_adjust_stock(r, tenant_id: int, user_id: int) -> AdjustStockToCommand:
    return AdjustStockToCommand(tenant_id, user_id, r.product_id, r.branch_id, r.new_stock, r.reason)


def to_start_audit(r, tenant_id: int, user_id: int) -> StartAuditCommand:
    return StartAuditCommand(tenant_id, user_id, r.branch_id, r.notes)


def to_count_item(audit_id: int, r, tenant_id: int) -> CountAuditItemCommand:
    return CountAuditItemCommand(tenant_id, audit_id, r.product_id, r.counted_stock, r.notes)


def to_complete_audit(audit_id: int, tenant_id: int, user_id: int) -> CompleteAuditCommand:
    return CompleteAuditCommand(tenant_id, user_id, audit_id)
