from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.database import get_db
from app.presentation.dependencies import get_current_tenant, get_current_user, require_role, require_permission
from app.infrastructure.persistence.models.identity.user import User, UserRole
from app.application.inventory.stock_use_cases import AddStock, AdjustStockTo, RemoveStock
from app.presentation.api.v1.inventory.deps import (
    get_add_stock, get_adjust_stock, get_remove_stock, to_add_stock, to_adjust_stock, to_remove_stock,
)
from app.presentation.schemas.catalog.product import AddStockRequest, RemoveStockRequest, AdjustStockRequest, InventoryMovementOut
from app.infrastructure.persistence.repositories.inventory.inventory_movement_repo import InventoryMovementRepository
from app.application.shared.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from app.infrastructure.persistence.models.inventory.inventory_movement import MovementType
from typing import Optional, List
from fastapi import Query
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedResponse[InventoryMovementOut])
async def list_movements(
    pagination: PaginationParams = Depends(),
    product_id: Optional[int] = Query(None, description="Filtrar por producto"),
    movement_type: Optional[MovementType] = Query(None, description="Filtrar por tipo de movimiento"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista historial de movimientos de inventario"""
    repo = InventoryMovementRepository(db)

    if product_id:
        items, total = await repo.get_by_product(product_id, tenant_id, pagination)
    elif movement_type:
        items, total = await repo.get_by_type(movement_type, tenant_id, pagination)
    else:
        items, total = await repo.get_paginated(pagination, tenant_id)

    metadata = create_pagination_metadata(pagination.page, pagination.page_size, total)
    return PaginatedResponse(items=items, metadata=metadata)


@router.post("/add-stock", response_model=InventoryMovementOut)
async def add_stock(
    request: AddStockRequest,
    current_user: User = Depends(require_permission("inventory:adjust")),
    use_case: AddStock = Depends(get_add_stock),
    db: AsyncSession = Depends(get_db)
):
    """Agrega stock a un producto (Solo Admins/Managers)"""
    movement_id = await use_case.execute(to_add_stock(request, current_user.tenant_id, current_user.id))
    return await InventoryMovementRepository(db).get_by_id(movement_id, current_user.tenant_id)


@router.post("/remove-stock", response_model=InventoryMovementOut)
async def remove_stock(
    request: RemoveStockRequest,
    current_user: User = Depends(require_permission("inventory:adjust")),
    use_case: RemoveStock = Depends(get_remove_stock),
    db: AsyncSession = Depends(get_db)
):
    """Remueve stock de un producto (Solo Admins/Managers)"""
    movement_id = await use_case.execute(to_remove_stock(request, current_user.tenant_id, current_user.id))
    return await InventoryMovementRepository(db).get_by_id(movement_id, current_user.tenant_id)


@router.post("/adjust-stock", response_model=InventoryMovementOut)
async def adjust_stock(
    request: AdjustStockRequest,
    current_user: User = Depends(require_permission("inventory:adjust")),
    use_case: AdjustStockTo = Depends(get_adjust_stock),
    db: AsyncSession = Depends(get_db)
):
    """Ajusta el stock de un producto a un valor específico (Solo Admins/Managers)"""
    movement_id = await use_case.execute(to_adjust_stock(request, current_user.tenant_id, current_user.id))
    return await InventoryMovementRepository(db).get_by_id(movement_id, current_user.tenant_id)


@router.get("/kardex/{product_id}", response_model=List[InventoryMovementOut])
async def get_kardex(
    product_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el historial completo (sin paginación) de movimientos para un producto (Kardex)"""
    repo = InventoryMovementRepository(db)
    items, _ = await repo.get_by_product(product_id, tenant_id)
    return items
