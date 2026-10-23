from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.infrastructure.persistence.database import get_db
from app.presentation.dependencies import get_current_tenant, get_current_user, require_role, require_permission
from app.presentation.schemas.sales.sale import SaleCreate, SaleResponse, PaginatedSaleResponse
from app.infrastructure.persistence.repositories.sales.sale_repo import SaleRepository
from app.infrastructure.persistence.repositories.identity.tenant_repo import TenantRepository
from app.infrastructure.persistence.models.identity.user import User, UserRole
from app.infrastructure.external.ticket_generator import TicketGenerator
from fastapi.responses import StreamingResponse

from datetime import datetime

from app.application.inventory.picking import GetPickingList
from app.application.sales.use_cases import AnnulSale, CreateSale
from app.infrastructure.persistence.repositories.inventory.picking_reader import SqlAlchemyPickingReader
from app.infrastructure.external.webhook_service import WebhookService
from app.infrastructure.persistence.database import async_session
from app.presentation.api.v1.sales.deps import get_annul_sale, get_create_sale, to_annul_command, to_create_command

router = APIRouter(tags=["Sales"])

@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_in: SaleCreate,
    background_tasks: BackgroundTasks,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    create_sale_use_case: CreateSale = Depends(get_create_sale),
    db: AsyncSession = Depends(get_db)
):
    """Realiza una nueva venta"""
    sale_id = await create_sale_use_case.execute(
        to_create_command(sale_in, tenant_id, current_user.id)
    )
    sale = await SaleRepository(db).get_by_id(sale_id, tenant_id)

    # Disparar Webhook en segundo plano
    background_tasks.add_task(
        WebhookService.trigger_webhook_task,
        tenant_id,
        "sale.created",
        {"sale_id": sale.id, "total": float(sale.total_amount), "items_count": len(sale.items)},
        async_session
    )
    return sale

from app.application.shared.pagination import PaginationParams, create_pagination_metadata

@router.get("/", response_model=PaginatedSaleResponse)
async def list_sales(
    pagination: PaginationParams = Depends(),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista las ventas paginadas con filtros estándar"""
    repo = SaleRepository(db)
    items, total = await repo.get_sales_paginated(
        tenant_id=tenant_id,
        pagination=pagination,
        start_date=start_date,
        end_date=end_date,
        status=status,
        payment_method=payment_method,
        search=search,
        seller_id=seller_id
    )
    
    metadata = create_pagination_metadata(pagination.page, pagination.page_size, total)
    return PaginatedSaleResponse(items=items, metadata=metadata)

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
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN])),
    annul_sale_use_case: AnnulSale = Depends(get_annul_sale),
    db: AsyncSession = Depends(get_db)
):
    """Anula una venta y revierte el stock (Solo Admins/Managers)"""
    await annul_sale_use_case.execute(to_annul_command(sale_id, current_user.tenant_id, current_user.id))
    return await SaleRepository(db).get_by_id(sale_id, current_user.tenant_id)

@router.get("/{sale_id}/picking-list")
async def get_picking_list(
    sale_id: int,
    current_user: User = Depends(require_permission("sales:picking")),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene la lista de surtido (picking) optimizada por ubicación"""
    return await GetPickingList(SqlAlchemyPickingReader(db)).execute(current_user.tenant_id, sale_id)
