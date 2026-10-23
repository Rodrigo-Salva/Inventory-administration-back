"""Composition root de compras: conecta casos de uso con sus adaptadores."""

from decimal import Decimal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.dto import (
    CreatePurchaseCommand,
    PurchaseActionCommand,
    PurchaseItemInput,
)
from app.application.purchasing.use_cases import CancelPurchase, CreatePurchase, ReceivePurchase
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.inventory.branch_stock_gateway import SqlAlchemyBranchStock
from app.infrastructure.persistence.repositories.purchasing.purchase_store import SqlAlchemyPurchaseStore
from app.infrastructure.persistence.tenant_resources import SqlAlchemyTenantResources
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.presentation.schemas.purchasing.purchase import PurchaseCreate


def get_create_purchase(db: AsyncSession = Depends(get_db)) -> CreatePurchase:
    return CreatePurchase(
        SqlAlchemyPurchaseStore(db), SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db)
    )


def get_receive_purchase(db: AsyncSession = Depends(get_db)) -> ReceivePurchase:
    return ReceivePurchase(
        SqlAlchemyPurchaseStore(db), SqlAlchemyBranchStock(db), SqlAlchemyUnitOfWork(db)
    )


def get_cancel_purchase(db: AsyncSession = Depends(get_db)) -> CancelPurchase:
    return CancelPurchase(SqlAlchemyPurchaseStore(db), SqlAlchemyUnitOfWork(db))


def to_create_command(payload: PurchaseCreate, tenant_id: int, user_id: int) -> CreatePurchaseCommand:
    return CreatePurchaseCommand(
        tenant_id=tenant_id,
        user_id=user_id,
        supplier_id=payload.supplier_id,
        branch_id=payload.branch_id,
        items=tuple(
            PurchaseItemInput(i.product_id, i.quantity, Decimal(str(i.unit_cost))) for i in payload.items
        ),
        reference_number=payload.reference_number,
        notes=payload.notes,
        due_date=payload.due_date,
    )


def to_action(purchase_id: int, tenant_id: int, user_id: int) -> PurchaseActionCommand:
    return PurchaseActionCommand(purchase_id=purchase_id, tenant_id=tenant_id, user_id=user_id)
