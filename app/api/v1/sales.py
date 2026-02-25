from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ...models import get_db
from ...dependencies import get_current_tenant, get_current_user
from ...schemas.sale import SaleCreate, SaleResponse, PaginatedSaleResponse
from ...repositories.sale_repo import SaleRepository
from ...repositories.tenant_repo import TenantRepository
from ...models.user import User
from ...services.ticket_generator import TicketGenerator
from fastapi.responses import StreamingResponse

from datetime import datetime

router = APIRouter(tags=["Sales"])

@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_in: SaleCreate,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Realiza una nueva venta"""
    repo = SaleRepository(db)
    try:
        sale = await repo.create_sale(tenant_id, current_user.id, sale_in)
        return sale
    except Exception as e:
        # Aquí podrías manejar excepciones específicas como InsufficientStockException
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=PaginatedSaleResponse)
async def list_sales(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista las ventas paginadas"""
    repo = SaleRepository(db)
    items, total = await repo.get_sales_paginated(
        tenant_id, page, size, start_date, end_date, status, payment_method, search, seller_id
    )
    
    pages = (total + size - 1) // size
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de una venta específica"""
    repo = SaleRepository(db)
    sale = await repo.get_by_id(sale_id, tenant_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return sale

@router.get("/{sale_id}/ticket")
async def get_sale_ticket(
    sale_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Genera un ticket PDF para una venta"""
    sale_repo = SaleRepository(db)
    tenant_repo = TenantRepository(db)
    
    sale = await sale_repo.get_by_id(sale_id, tenant_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    tenant = await tenant_repo.get_by_id(tenant_id)
    tenant_name = tenant.name if tenant else "Mi Negocio"
    
    pdf_buffer = TicketGenerator.generate_ticket(sale, tenant_name)
    
    filename = f"Ticket_{sale_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
@router.post("/{sale_id}/annul", response_model=SaleResponse)
async def annul_sale(
    sale_id: int,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Anula una venta y revierte el stock"""
    repo = SaleRepository(db)
    sale = await repo.annul_sale(sale_id, tenant_id, current_user.id)
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return sale
