from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.base import get_db
from ...dependencies import require_permission
from ...models.user import User
from ...schemas.stock_transfer import StockTransferCreate, StockTransferOut, StockTransferUpdate
from ...repositories.stock_transfer_repo import StockTransferRepository

router = APIRouter()

@router.get("/stats")
async def get_transfer_stats(
    current_user: User = Depends(require_permission("transfers:view")),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas generales de los traslados"""
    repo = StockTransferRepository(db)
    return await repo.get_stats(current_user.tenant_id)


@router.get("/", response_model=List[StockTransferOut])
async def get_transfers(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_permission("transfers:view")),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el listado de traslados entre sucursales"""
    repo = StockTransferRepository(db)
    return await repo.get_all(current_user.tenant_id, skip=skip, limit=limit)

@router.get("/{transfer_id}", response_model=StockTransferOut)
async def get_transfer(
    transfer_id: int,
    current_user: User = Depends(require_permission("transfers:view")),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de un traslado específico"""
    repo = StockTransferRepository(db)
    transfer = await repo.get_by_id(transfer_id, current_user.tenant_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Traslado no encontrado")
    return transfer

@router.post("/", response_model=StockTransferOut, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    obj_in: StockTransferCreate,
    current_user: User = Depends(require_permission("transfers:create")),
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo traslado (en estado pendiente o completado directamente)"""
    repo = StockTransferRepository(db)
    try:
        transfer = await repo.create(obj_in, current_user.id, current_user.tenant_id)
        await db.commit()
        # Refrescar para devolver con relaciones cargadas
        return await repo.get_by_id(transfer.id, current_user.tenant_id)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{transfer_id}/complete", response_model=StockTransferOut)
async def complete_transfer(
    transfer_id: int,
    current_user: User = Depends(require_permission("transfers:manage")),
    db: AsyncSession = Depends(get_db)
):
    """Completa un traslado pendiente y actualiza stocks"""
    repo = StockTransferRepository(db)
    transfer = await repo.get_by_id(transfer_id, current_user.tenant_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Traslado no encontrado")
    
    try:
        updated_transfer = await repo.complete_transfer(transfer)
        await db.commit()
        return updated_transfer
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{transfer_id}/cancel", response_model=StockTransferOut)
async def cancel_transfer(
    transfer_id: int,
    current_user: User = Depends(require_permission("transfers:manage")),
    db: AsyncSession = Depends(get_db)
):
    """Cancela un traslado pendiente"""
    repo = StockTransferRepository(db)
    transfer = await repo.get_by_id(transfer_id, current_user.tenant_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Traslado no encontrado")
    
    try:
        updated_transfer = await repo.cancel_transfer(transfer)
        await db.commit()
        return updated_transfer
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
