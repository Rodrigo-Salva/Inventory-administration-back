from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ...models import get_db
from ...dependencies import get_current_tenant, get_current_user
from ...schemas.quote import QuoteCreate, QuoteResponse, PaginatedQuoteResponse
from ...repositories.quote_repo import QuoteRepository
from ...services.quote_service import QuoteService
from ...models.user import User
from ...models.sale import PaymentMethod
from ...schemas.sale import SaleResponse

from datetime import datetime
from ...core.pagination import PaginationParams, create_pagination_metadata

router = APIRouter(tags=["Quotes"])

@router.post("/", response_model=QuoteResponse)
async def create_quote(
    quote_in: QuoteCreate,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Crea una nueva cotización sin descontar inventario"""
    repo = QuoteRepository(db)
    try:
        quote = await repo.create_quote(tenant_id, current_user.id, quote_in)
        return quote
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=PaginatedQuoteResponse)
async def list_quotes(
    pagination: PaginationParams = Depends(),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista las cotizaciones paginadas con filtros estándar"""
    repo = QuoteRepository(db)
    items, total = await repo.get_quotes_paginated(
        tenant_id=tenant_id,
        pagination=pagination,
        start_date=start_date,
        end_date=end_date,
        status=status,
        customer_id=customer_id,
        search=search
    )
    
    metadata = create_pagination_metadata(pagination.page, pagination.page_size, total)
    return PaginatedQuoteResponse(items=items, metadata=metadata)

@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de una cotización específica"""
    repo = QuoteRepository(db)
    quote = await repo.get_by_id(quote_id, tenant_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return quote

@router.post("/{quote_id}/convert", response_model=SaleResponse)
async def convert_quote_to_sale(
    quote_id: int,
    payment_method: PaymentMethod = PaymentMethod.CASH,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Convierte una cotización en una venta (descuenta inventario)"""
    service = QuoteService(db)
    sale = await service.convert_to_sale(quote_id, tenant_id, current_user.id, payment_method)
    return sale
