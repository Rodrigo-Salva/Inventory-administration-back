from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.base import get_db
from ...models.user import User
from ...dependencies import get_current_user
from ...schemas.cash_session import CashSessionCreate, CashSessionResponse, CashSessionClose
from ...repositories.cash_session_repo import CashSessionRepository
from typing import Optional

router = APIRouter(tags=["POS"])

@router.get("/current-session", response_model=Optional[CashSessionResponse])
async def get_current_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verifica si el usuario actual tiene una sesión de caja abierta"""
    repo = CashSessionRepository(db)
    session = await repo.get_active_session(current_user.tenant_id, current_user.id)
    return session

@router.post("/open-session", response_model=CashSessionResponse)
async def open_session(
    session_in: CashSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Abre una nueva sesión de caja (turno)"""
    repo = CashSessionRepository(db)
    try:
        session = await repo.open_session(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            opening_balance=session_in.opening_balance,
            notes=session_in.notes
        )
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/close-session", response_model=CashSessionResponse)
async def close_session(
    session_close: CashSessionClose,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cierra la sesión de caja actual"""
    repo = CashSessionRepository(db)
    active_session = await repo.get_active_session(current_user.tenant_id, current_user.id)
    
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes una sesión de caja abierta."
        )

    try:
        session = await repo.close_session(
            session_id=active_session.id,
            tenant_id=current_user.tenant_id,
            closing_balance=session_close.closing_balance
        )
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
