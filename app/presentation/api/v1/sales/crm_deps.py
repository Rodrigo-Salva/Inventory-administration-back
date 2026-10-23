"""Composition root de clientes y cotizaciones."""

from decimal import Decimal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.crm_dto import CreateQuoteCommand, QuoteLine
from app.application.sales.crm_use_cases import (
    ConvertQuote,
    CreateCustomer,
    CreateQuote,
    DeleteCustomer,
    UpdateCustomer,
)
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.sales.crm_gateway import (
    SqlAlchemyCustomerStore,
    SqlAlchemyQuoteStore,
)
from app.infrastructure.persistence.tenant_resources import SqlAlchemyTenantResources
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.presentation.api.v1.sales.deps import build_create_sale
from app.presentation.schemas.sales.quote import QuoteCreate


def get_create_customer(db: AsyncSession = Depends(get_db)) -> CreateCustomer:
    return CreateCustomer(SqlAlchemyCustomerStore(db), SqlAlchemyUnitOfWork(db))


def get_update_customer(db: AsyncSession = Depends(get_db)) -> UpdateCustomer:
    return UpdateCustomer(SqlAlchemyCustomerStore(db), SqlAlchemyUnitOfWork(db))


def get_delete_customer(db: AsyncSession = Depends(get_db)) -> DeleteCustomer:
    return DeleteCustomer(SqlAlchemyCustomerStore(db), SqlAlchemyUnitOfWork(db))


def get_create_quote(db: AsyncSession = Depends(get_db)) -> CreateQuote:
    return CreateQuote(SqlAlchemyQuoteStore(db), SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db))


def get_convert_quote(db: AsyncSession = Depends(get_db)) -> ConvertQuote:
    return ConvertQuote(SqlAlchemyQuoteStore(db), build_create_sale(db), SqlAlchemyUnitOfWork(db))


def to_quote_command(payload: QuoteCreate, tenant_id: int, user_id: int) -> CreateQuoteCommand:
    return CreateQuoteCommand(
        tenant_id=tenant_id,
        user_id=user_id,
        valid_until=payload.valid_until,
        lines=tuple(QuoteLine(i.product_id, i.quantity, Decimal(str(i.unit_price))) for i in payload.items),
        customer_id=payload.customer_id,
        notes=payload.notes,
    )
