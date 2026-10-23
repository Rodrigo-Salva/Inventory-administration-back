from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.infrastructure.persistence.repositories.base_repository import BaseRepository
from app.infrastructure.persistence.models.sales.cash_session import CashSession, CashSessionStatus
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
