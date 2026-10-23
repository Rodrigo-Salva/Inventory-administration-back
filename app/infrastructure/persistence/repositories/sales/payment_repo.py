from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.infrastructure.persistence.repositories.base_repository import BaseRepository
from app.infrastructure.persistence.models.sales.payment import Payment
from app.infrastructure.persistence.models.sales.credit import Credit, CreditStatus
from app.infrastructure.persistence.models.sales.customer import Customer
from typing import List, Optional
from decimal import Decimal

class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: AsyncSession):
        super().__init__(Payment, db)

    async def get_payments_by_credit(self, tenant_id: int, credit_id: int) -> List[Payment]:
        """Obtiene el historial de abonos de un crédito"""
        query = select(Payment).where(
            and_(
                Payment.tenant_id == tenant_id,
                Payment.credit_id == credit_id
            )
        ).order_by(Payment.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
