"""Composition root de ventas: conecta casos de uso con sus adaptadores."""

from decimal import Decimal

from fastapi import BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.dto import AnnulSaleCommand, CreateSaleCommand, SaleLine
from app.application.sales.use_cases import AnnulSale, CreateSale
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.inventory.stock_gateway import SqlAlchemyInventory
from app.infrastructure.persistence.repositories.inventory.branch_resolver import SqlAlchemyBranchResolver
from app.infrastructure.persistence.repositories.sales.cash_gateway import SqlAlchemyCashSessions
from app.infrastructure.persistence.repositories.sales.credit_gateway import SqlAlchemyCredit
from app.infrastructure.persistence.repositories.sales.loyalty_gateway import SqlAlchemyLoyalty
from app.infrastructure.persistence.repositories.sales.sale_store import SqlAlchemySaleStore
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.presentation.schemas.sales.sale import SaleCreate


def build_create_sale(db: AsyncSession, scheduler=None) -> CreateSale:
    return CreateSale(
        sales=SqlAlchemySaleStore(db),
        inventory=SqlAlchemyInventory(db, scheduler),
        loyalty=SqlAlchemyLoyalty(db),
        credit=SqlAlchemyCredit(db),
        uow=SqlAlchemyUnitOfWork(db),
        cash_sessions=SqlAlchemyCashSessions(db),
        branches=SqlAlchemyBranchResolver(db),
    )


def get_create_sale(
    background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> CreateSale:
    return build_create_sale(db, background_tasks)


def get_annul_sale(db: AsyncSession = Depends(get_db)) -> AnnulSale:
    return AnnulSale(
        sales=SqlAlchemySaleStore(db),
        inventory=SqlAlchemyInventory(db),
        loyalty=SqlAlchemyLoyalty(db),
        credit=SqlAlchemyCredit(db),
        uow=SqlAlchemyUnitOfWork(db),
    )


def to_create_command(payload: SaleCreate, tenant_id: int, user_id: int) -> CreateSaleCommand:
    return CreateSaleCommand(
        tenant_id=tenant_id,
        user_id=user_id,
        lines=tuple(
            SaleLine(i.product_id, i.quantity, Decimal(str(i.unit_price)), i.batch_id)
            for i in payload.items
        ),
        payment_method=getattr(payload.payment_method, "value", payload.payment_method),
        notes=payload.notes,
        customer_id=payload.customer_id,
        redeemed_points=payload.redeemed_points or 0,
        branch_id=payload.branch_id,
    )


def to_annul_command(sale_id: int, tenant_id: int, user_id: int) -> AnnulSaleCommand:
    return AnnulSaleCommand(sale_id=sale_id, tenant_id=tenant_id, user_id=user_id)
