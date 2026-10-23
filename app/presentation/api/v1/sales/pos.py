from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.cash_dto import CloseCashSessionCommand, OpenCashSessionCommand
from app.application.sales.cash_use_cases import CloseCashSession, OpenCashSession
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.sales.cash_session_repo import CashSessionRepository
from app.presentation.api.v1.sales.cash_deps import get_close_cash_session, get_open_cash_session
from app.presentation.dependencies import get_current_user
from app.presentation.schemas.sales.cash_session import CashSessionClose, CashSessionCreate, CashSessionResponse

router = APIRouter(tags=["POS"])


@router.get("/current-session", response_model=Optional[CashSessionResponse])
async def get_current_session(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Verifica si el usuario actual tiene una sesión de caja abierta"""
    return await CashSessionRepository(db).get_active_session(current_user.tenant_id, current_user.id)


@router.post("/open-session", response_model=CashSessionResponse)
async def open_session(
    session_in: CashSessionCreate,
    use_case: OpenCashSession = Depends(get_open_cash_session),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Abre una nueva sesión de caja (turno)"""
    session_id = await use_case.execute(
        OpenCashSessionCommand(
            current_user.tenant_id, current_user.id, session_in.opening_balance, session_in.notes
        )
    )
    return await CashSessionRepository(db).get_by_id(session_id, current_user.tenant_id)


@router.post("/close-session", response_model=CashSessionResponse)
async def close_session(
    session_close: CashSessionClose,
    use_case: CloseCashSession = Depends(get_close_cash_session),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cierra la sesión de caja actual y calcula el efectivo esperado"""
    session_id = await use_case.execute(
        CloseCashSessionCommand(current_user.tenant_id, current_user.id, session_close.closing_balance)
    )
    return await CashSessionRepository(db).get_by_id(session_id, current_user.tenant_id)
