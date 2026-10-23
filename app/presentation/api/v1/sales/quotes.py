from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.crm_dto import ConvertQuoteCommand
from app.application.sales.crm_use_cases import ConvertQuote, CreateQuote
from app.application.shared.pagination import PaginationParams, create_pagination_metadata
from app.domain.sales.errors import QuoteNotFoundError
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.models.sales.sale import PaymentMethod
from app.infrastructure.persistence.repositories.sales.quote_repo import QuoteRepository
from app.infrastructure.persistence.repositories.sales.sale_repo import SaleRepository
from app.presentation.api.v1.sales.crm_deps import get_convert_quote, get_create_quote, to_quote_command
from app.presentation.dependencies import get_current_tenant, get_current_user
from app.presentation.schemas.sales.quote import PaginatedQuoteResponse, QuoteCreate, QuoteResponse
from app.presentation.schemas.sales.sale import SaleResponse

router = APIRouter(tags=["Quotes"])


@router.post("/", response_model=QuoteResponse)
async def create_quote(
    quote_in: QuoteCreate,
    current_user: User = Depends(get_current_user),
    use_case: CreateQuote = Depends(get_create_quote),
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva cotización sin descontar inventario"""
    quote_id = await use_case.execute(to_quote_command(quote_in, current_user.tenant_id, current_user.id))
    return await QuoteRepository(db).get_by_id(quote_id, current_user.tenant_id)


@router.get("/", response_model=PaginatedQuoteResponse)
async def list_quotes(
    pagination: PaginationParams = Depends(),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Lista las cotizaciones paginadas con filtros estándar"""
    items, total = await QuoteRepository(db).get_quotes_paginated(
        tenant_id=tenant_id, pagination=pagination, start_date=start_date, end_date=end_date,
        status=status, customer_id=customer_id, search=search,
    )
    metadata = create_pagination_metadata(pagination.page, pagination.page_size, total)
    return PaginatedQuoteResponse(items=items, metadata=metadata)


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: int, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de una cotización específica"""
    quote = await QuoteRepository(db).get_by_id(quote_id, tenant_id)
    if not quote:
        raise QuoteNotFoundError()
    return quote


@router.post("/{quote_id}/convert", response_model=SaleResponse)
async def convert_quote_to_sale(
    quote_id: int,
    payment_method: PaymentMethod = PaymentMethod.CASH,
    current_user: User = Depends(get_current_user),
    use_case: ConvertQuote = Depends(get_convert_quote),
    db: AsyncSession = Depends(get_db),
):
    """Convierte una cotización en venta (descuenta inventario) de forma atómica"""
    sale_id = await use_case.execute(
        ConvertQuoteCommand(current_user.tenant_id, current_user.id, quote_id, payment_method.value)
    )
    return await SaleRepository(db).get_by_id(sale_id, current_user.tenant_id)
