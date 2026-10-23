from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.purchasing.purchase import PurchaseStatus
from app.presentation.dependencies import get_current_tenant, get_current_user
from app.infrastructure.persistence.repositories.purchasing.purchase_repo import PurchaseRepository
from app.presentation.schemas.purchasing.purchase import PurchaseCreate, PurchaseUpdate, PurchaseOut, PurchaseSummary
from app.application.shared.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from app.infrastructure.logging import get_logger

from app.application.purchasing.use_cases import CancelPurchase, CreatePurchase, ReceivePurchase
from app.infrastructure.persistence.models.identity.user import User
from app.presentation.api.v1.purchasing.deps import (
    get_cancel_purchase, get_create_purchase, get_receive_purchase, to_action, to_create_command,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_purchase_stats(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas generales de las compras"""
    repo = PurchaseRepository(db)
    return await repo.get_stats(tenant_id)


@router.get("/", response_model=PaginatedResponse[PurchaseSummary])
async def list_purchases(
    pagination: PaginationParams = Depends(),
    status: Optional[PurchaseStatus] = Query(None),
    supplier_id: Optional[int] = Query(None),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las compras con paginación y filtros"""
    repo = PurchaseRepository(db)
    purchases, total = await repo.get_filtered(
        tenant_id=tenant_id,
        status=status,
        supplier_id=supplier_id,
        pagination=pagination
    )
    
    # Mapear a summary (podríamos hacerlo en el repo si fuera más complejo)
    summaries = [
        PurchaseSummary(
            id=p.id,
            supplier_name=p.supplier.name if p.supplier else "N/A",
            total_amount=p.total_amount,
            status=p.status,
            created_at=p.created_at
        )
        for p in purchases
    ]
    
    return PaginatedResponse(
        items=summaries,
        metadata=create_pagination_metadata(
            total_items=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    )


@router.post("/", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    purchase_in: PurchaseCreate,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    use_case: CreatePurchase = Depends(get_create_purchase),
    db: AsyncSession = Depends(get_db)
):
    """Crea una nueva compra en estado Borrador"""
    purchase_id = await use_case.execute(to_create_command(purchase_in, tenant_id, current_user.id))
    return await PurchaseRepository(db).get_with_items(purchase_id, tenant_id)


@router.get("/{purchase_id}", response_model=PurchaseOut)
async def get_purchase(
    purchase_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle completo de una compra"""
    repo = PurchaseRepository(db)
    purchase = await repo.get_with_items(purchase_id, tenant_id)
    
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compra con ID {purchase_id} no encontrada"
        )
    
    return purchase


@router.post("/{purchase_id}/receive", response_model=PurchaseOut)
async def receive_purchase(
    purchase_id: int,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    use_case: ReceivePurchase = Depends(get_receive_purchase),
    db: AsyncSession = Depends(get_db)
):
    """Marca la compra como recibida y actualiza el inventario"""
    await use_case.execute(to_action(purchase_id, tenant_id, current_user.id))
    logger.info(f"Compra #{purchase_id} recibida. Inventario actualizado.")
    return await PurchaseRepository(db).get_with_items(purchase_id, tenant_id)


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_purchase(
    purchase_id: int,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    use_case: CancelPurchase = Depends(get_cancel_purchase),
):
    """Cancela una compra (solo si está en borrador)"""
    await use_case.execute(to_action(purchase_id, tenant_id, current_user.id))
    return None

@router.get("/{purchase_id}/pdf")
async def export_purchase_pdf(
    purchase_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Genera un reporte PDF profesional de una orden de compra"""
    from app.infrastructure.external.report_generator import ReportGenerator
    from app.infrastructure.persistence.repositories.identity.tenant_repo import TenantRepository
    
    repo = PurchaseRepository(db)
    t_repo = TenantRepository(db)
    
    purchase = await repo.get_with_items(purchase_id, tenant_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
        
    tenant = await t_repo.get_by_id(tenant_id)
    tenant_name = tenant.name if tenant else "Mi Negocio"
    
    pdf_buffer = ReportGenerator.generate_purchase_order_pdf(purchase, tenant_name)
    
    filename = f"Orden_Compra_{purchase_id}.pdf"
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
