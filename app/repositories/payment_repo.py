from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from .base_repository import BaseRepository
from ..models.payment import Payment
from ..models.credit import Credit, CreditStatus
from ..models.customer import Customer
from typing import List, Optional
from decimal import Decimal

class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: AsyncSession):
        super().__init__(Payment, db)

    async def register_payment(self, tenant_id: int, credit_id: int, amount: Decimal, payment_method: str, notes: Optional[str] = None) -> Payment:
        """Registra un abono a un crédito y actualiza los saldos"""
        
        # 1. Obtener el crédito
        query_credit = select(Credit).where(
            and_(Credit.id == credit_id, Credit.tenant_id == tenant_id)
        )
        res_credit = await self.db.execute(query_credit)
        credit = res_credit.scalar_one_or_none()
        
        if not credit:
            raise Exception("Crédito no encontrado.")
            
        if credit.status == CreditStatus.PAID:
            raise Exception("Este crédito ya está pagado.")

        if amount > credit.remaining_amount:
            raise Exception(f"El monto del abono ({amount}) supera el saldo pendiente ({credit.remaining_amount}).")

        # 2. Crear el pago
        payment = Payment(
            tenant_id=tenant_id,
            credit_id=credit_id,
            amount=amount,
            payment_method=payment_method,
            notes=notes
        )
        self.db.add(payment)

        # 3. Actualizar el saldo del crédito
        credit.remaining_amount -= amount
        if credit.remaining_amount <= 0:
            credit.status = CreditStatus.PAID
            credit.remaining_amount = 0

        # 4. Actualizar el saldo del cliente
        query_customer = select(Customer).where(Customer.id == credit.customer_id)
        res_customer = await self.db.execute(query_customer)
        customer = res_customer.scalar_one()
        customer.current_balance -= amount

        await self.db.flush()
        return payment

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
