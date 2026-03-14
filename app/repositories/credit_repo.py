from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from .base_repository import BaseRepository
from ..models.credit import Credit, CreditStatus
from ..models.customer import Customer
from typing import List, Optional
from decimal import Decimal

class CreditRepository(BaseRepository[Credit]):
    def __init__(self, db: AsyncSession):
        super().__init__(Credit, db)

    async def get_by_customer(self, tenant_id: int, customer_id: int) -> List[Credit]:
        """Obtiene todos los créditos de un cliente específico"""
        query = select(Credit).where(
            and_(
                Credit.tenant_id == tenant_id,
                Credit.customer_id == customer_id
            )
        ).order_by(Credit.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_pending_by_customer(self, tenant_id: int, customer_id: int) -> List[Credit]:
        """Obtiene créditos con saldo pendiente de un cliente"""
        query = select(Credit).where(
            and_(
                Credit.tenant_id == tenant_id,
                Credit.customer_id == customer_id,
                Credit.status == CreditStatus.PENDING
            )
        ).order_by(Credit.due_date.asc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def check_credit_availability(self, tenant_id: int, customer_id: int, amount: Decimal) -> bool:
        """Verifica si el cliente tiene cupo disponible para un nuevo crédito"""
        query = select(Customer).where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.id == customer_id
            )
        )
        result = await self.db.execute(query)
        customer = result.scalar_one_or_none()
        
        if not customer:
            return False
            
        return (customer.credit_limit - customer.current_balance) >= amount

    async def create_from_sale(self, tenant_id: int, customer_id: int, sale_id: int, total_amount: Decimal, due_days: int = 30) -> Credit:
        """Crea un nuevo crédito a partir de una venta"""
        from datetime import datetime, timedelta
        
        due_date = datetime.utcnow() + timedelta(days=due_days)
        
        credit = Credit(
            tenant_id=tenant_id,
            customer_id=customer_id,
            sale_id=sale_id,
            total_amount=total_amount,
            remaining_amount=total_amount,
            status=CreditStatus.PENDING,
            due_date=due_date
        )
        
        self.db.add(credit)
        
        # Actualizar el saldo del cliente
        query = select(Customer).where(Customer.id == customer_id)
        res = await self.db.execute(query)
        customer = res.scalar_one()
        customer.current_balance += total_amount
        
        await self.db.flush()
        return credit
