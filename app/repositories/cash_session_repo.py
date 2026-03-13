from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from .base_repository import BaseRepository
from ..models.cash_session import CashSession, CashSessionStatus
from datetime import datetime
from typing import Optional

class CashSessionRepository(BaseRepository[CashSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(CashSession, db)

    async def get_active_session(self, tenant_id: int, user_id: int) -> Optional[CashSession]:
        """Obtiene la sesión abierta actual del usuario"""
        query = select(CashSession).where(
            and_(
                CashSession.tenant_id == tenant_id,
                CashSession.user_id == user_id,
                CashSession.status == CashSessionStatus.OPEN
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def open_session(self, tenant_id: int, user_id: int, opening_balance: float, notes: Optional[str] = None) -> CashSession:
        """Abre una nueva sesión de caja"""
        # Verificar si ya tiene una abierta
        existing = await self.get_active_session(tenant_id, user_id)
        if existing:
            raise Exception("Ya tienes una sesión de caja abierta.")

        new_session = CashSession(
            tenant_id=tenant_id,
            user_id=user_id,
            opening_balance=opening_balance,
            status=CashSessionStatus.OPEN,
            opened_at=datetime.utcnow(),
            notes=notes
        )
        self.db.add(new_session)
        await self.db.commit()
        await self.db.refresh(new_session)
        return new_session

    async def close_session(self, session_id: int, tenant_id: int, closing_balance: float) -> CashSession:
        """Cierra una sesión de caja calculando el balance esperado"""
        session = await self.get_by_id(session_id, tenant_id)
        if not session or session.status == CashSessionStatus.CLOSED:
            raise Exception("Sesión no encontrada o ya cerrada.")

        # Calcular balance esperado (opening + ventas en efectivo)
        # 1. Calcular balance esperado: Saldo Inicial + Ventas - Gastos
        from ..models.sale import Sale
        result_sales = await self.db.execute(
            select(func.sum(Sale.total_amount)).where(
                Sale.cash_session_id == session_id,
                Sale.status == "completed"
            )
        )
        total_sales = result_sales.scalar() or 0
        
        # Obtener gastos de la sesión
        from ..models.expense import Expense
        result_expenses = await self.db.execute(
            select(func.sum(Expense.amount)).where(
                Expense.cash_session_id == session_id
            )
        )
        total_expenses = result_expenses.scalar() or 0

        session.expected_balance = session.opening_balance + total_sales - total_expenses
        session.closing_balance = closing_balance
        session.status = CashSessionStatus.CLOSED
        session.closed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(session)
        return session
