from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...models import get_db
from ...dependencies import get_current_tenant
from ...services.inventory_service import InventoryService
from ...schemas.product import (
    AddStockRequest,
    RemoveStockRequest,
    AdjustStockRequest,
    InventoryMovementOut
)
from ...repositories.inventory_movement_repo import InventoryMovementRepository
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from ...models.inventory_movement import MovementType
from typing import Optional, List
from fastapi import Query
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedResponse[InventoryMovementOut])
async def list_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: Optional[int] = Query(None, description="Filtrar por producto"),
    movement_type: Optional[MovementType] = Query(None, description="Filtrar por tipo de movimiento"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista historial de movimientos de inventario"""
    try:
        repo = InventoryMovementRepository(db)
        pagination = PaginationParams(page=page, page_size=page_size)
        
        if product_id:
            items, total = await repo.get_by_product(product_id, tenant_id, pagination)
        elif movement_type:
            items, total = await repo.get_by_type(movement_type, tenant_id, pagination)
        else:
            items, total = await repo.get_paginated(pagination, tenant_id)
            
        metadata = create_pagination_metadata(page, page_size, total)
        return PaginatedResponse(items=items, metadata=metadata)
        
    except Exception as e:
        logger.error(f"Error listando movimientos: {e}")
        import traceback
        traceback.print_exc()
        raise e


@router.post("/add-stock", response_model=InventoryMovementOut, status_code=status.HTTP_201_CREATED)
async def add_stock(
    request: AddStockRequest,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Agrega stock a un producto"""
    service = InventoryService(db)
    
    movement = await service.add_stock(
        product_id=request.product_id,
        quantity=request.quantity,
        tenant_id=tenant_id,
        unit_cost=request.unit_cost,
        reference=request.reference,
        notes=request.notes
    )
    
    return movement


@router.post("/remove-stock", response_model=InventoryMovementOut, status_code=status.HTTP_201_CREATED)
async def remove_stock(
    request: RemoveStockRequest,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Remueve stock de un producto"""
    service = InventoryService(db)
    
    movement = await service.remove_stock(
        product_id=request.product_id,
        quantity=request.quantity,
        tenant_id=tenant_id,
        reference=request.reference,
        notes=request.notes,
        allow_negative=request.allow_negative
    )
    
    return movement


@router.post("/adjust-stock", response_model=InventoryMovementOut, status_code=status.HTTP_201_CREATED)
async def adjust_stock(
    request: AdjustStockRequest,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Ajusta el stock de un producto a un valor específico"""
    service = InventoryService(db)
    
    movement = await service.adjust_stock(
        product_id=request.product_id,
        new_stock=request.new_stock,
        tenant_id=tenant_id,
        reason=request.reason
    )
    
    return movement
