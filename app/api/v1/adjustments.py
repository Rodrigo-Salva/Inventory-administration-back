from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.base import get_db
from ...dependencies import require_role
from ...models.user import User, UserRole
from ...schemas.adjustment import AdjustmentCreate, AdjustmentOut
from ...repositories.adjustment_repo import AdjustmentRepository

router = APIRouter()

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
    db: AsyncSession = Depends(get_db)
):
    """Registra un nuevo ajuste de inventario y actualiza el stock"""
    repo = AdjustmentRepository(db)
    try:
        adjustment = await repo.create(obj_in, current_user.id, current_user.tenant_id)
        await db.commit()
        return adjustment
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
