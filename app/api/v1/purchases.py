from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import get_db, PurchaseStatus
from ...dependencies import get_current_tenant, get_current_user
from ...repositories import PurchaseRepository
from ...schemas.purchase import (
    PurchaseCreate,
    PurchaseUpdate,
    PurchaseOut,
    PurchaseSummary
)
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


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
    current_user_id: int = Depends(get_current_user), # Podríamos necesitar el ID del usuario
    db: AsyncSession = Depends(get_db)
):
    """Crea una nueva compra en estado Borrador"""
    repo = PurchaseRepository(db)
    
    # Calcular total
    total = sum(item.quantity * item.unit_cost for item in purchase_in.items)
    
    # Crear la compra base
    purchase_data = purchase_in.model_dump(exclude={"items"})
    purchase_data["tenant_id"] = tenant_id
    purchase_data["total_amount"] = total
    # purchase_data["user_id"] = current_user_id # Si el dependency devuelve el ID
    
    from ...models import Purchase, PurchaseItem
    new_purchase = Purchase(**purchase_data)
    db.add(new_purchase)
    await db.flush() # Para obtener el ID
    
    # Crear los ítems
    for item_in in purchase_in.items:
        item = PurchaseItem(
            purchase_id=new_purchase.id,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            unit_cost=item_in.unit_cost,
            subtotal=item_in.quantity * item_in.unit_cost
        )
        db.add(item)
    
    await db.commit()
    return await repo.get_with_items(new_purchase.id, tenant_id)


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
    db: AsyncSession = Depends(get_db)
):
    """Marca la compra como recibida y actualiza el inventario"""
    repo = PurchaseRepository(db)
    
    purchase = await repo.receive_purchase(purchase_id, tenant_id)
    
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo recibir la compra. Verifique que exista y esté en estado Borrador."
        )
    
    await db.commit()
    logger.info(f"Compra #{purchase_id} recibida. Inventario actualizado.")
    return purchase


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_purchase(
    purchase_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Cancela una compra (solo si está en borrador)"""
    repo = PurchaseRepository(db)
    purchase = await repo.get_by_id(purchase_id, tenant_id)
    
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compra no encontrada"
        )
    
    if purchase.status != PurchaseStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden cancelar compras en estado Borrador"
        )
    
    purchase.status = PurchaseStatus.CANCELLED
    await db.commit()
    return None

@router.get("/{purchase_id}/pdf")
async def export_purchase_pdf(
    purchase_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Genera un reporte PDF profesional de una orden de compra"""
    from ...services.report_generator import ReportGenerator
    from ...repositories.tenant_repo import TenantRepository
    
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
