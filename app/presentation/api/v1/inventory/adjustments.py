from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.database import get_db
from app.presentation.dependencies import require_role
from app.infrastructure.persistence.models.identity.user import User, UserRole
from app.presentation.schemas.inventory.adjustment import AdjustmentCreate, AdjustmentOut
from app.infrastructure.persistence.repositories.inventory.adjustment_repo import AdjustmentRepository

from app.application.inventory.use_cases import CreateAdjustment
from app.presentation.api.v1.inventory.deps import get_create_adjustment, to_adjustment_command

router = APIRouter()

@router.get("/stats")
async def get_adjustment_stats(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas de ajustes de inventario"""
    repo = AdjustmentRepository(db)
    return await repo.get_stats(current_user.tenant_id)

@router.get("/", response_model=List[AdjustmentOut])
async def get_adjustments(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Lista los ajustes de inventario registrados"""
    repo = AdjustmentRepository(db)
    return await repo.get_all(current_user.tenant_id, skip=skip, limit=limit)

@router.post("/", response_model=AdjustmentOut, status_code=status.HTTP_201_CREATED)
async def create_adjustment(
    obj_in: AdjustmentCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN])),
    use_case: CreateAdjustment = Depends(get_create_adjustment),
    db: AsyncSession = Depends(get_db)
):
    """Registra un nuevo ajuste de inventario y actualiza el stock"""
    adjustment_id = await use_case.execute(
        to_adjustment_command(obj_in, current_user.tenant_id, current_user.id)
    )
    return await AdjustmentRepository(db).get_by_id(adjustment_id, current_user.tenant_id)
