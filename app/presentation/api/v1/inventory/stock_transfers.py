from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.database import get_db
from app.presentation.dependencies import require_permission
from app.infrastructure.persistence.models.identity.user import User
from app.presentation.schemas.inventory.stock_transfer import StockTransferCreate, StockTransferOut, StockTransferUpdate
from app.infrastructure.persistence.repositories.inventory.stock_transfer_repo import StockTransferRepository

from app.application.inventory.use_cases import CancelStockTransfer, CompleteStockTransfer, CreateStockTransfer
from app.presentation.api.v1.inventory.deps import (
    get_cancel_transfer, get_complete_transfer, get_create_transfer,
    to_transfer_action, to_transfer_command,
)

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
    use_case: CreateStockTransfer = Depends(get_create_transfer),
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo traslado (en estado pendiente o completado directamente)"""
    transfer_id = await use_case.execute(
        to_transfer_command(obj_in, current_user.tenant_id, current_user.id)
    )
    return await StockTransferRepository(db).get_by_id(transfer_id, current_user.tenant_id)

@router.put("/{transfer_id}/complete", response_model=StockTransferOut)
async def complete_transfer(
    transfer_id: int,
    current_user: User = Depends(require_permission("transfers:manage")),
    use_case: CompleteStockTransfer = Depends(get_complete_transfer),
    db: AsyncSession = Depends(get_db)
):
    """Completa un traslado pendiente y actualiza stocks"""
    await use_case.execute(to_transfer_action(transfer_id, current_user.tenant_id))
    return await StockTransferRepository(db).get_by_id(transfer_id, current_user.tenant_id)

@router.put("/{transfer_id}/cancel", response_model=StockTransferOut)
async def cancel_transfer(
    transfer_id: int,
    current_user: User = Depends(require_permission("transfers:manage")),
    use_case: CancelStockTransfer = Depends(get_cancel_transfer),
    db: AsyncSession = Depends(get_db)
):
    """Cancela un traslado pendiente"""
    await use_case.execute(to_transfer_action(transfer_id, current_user.tenant_id))
    return await StockTransferRepository(db).get_by_id(transfer_id, current_user.tenant_id)
