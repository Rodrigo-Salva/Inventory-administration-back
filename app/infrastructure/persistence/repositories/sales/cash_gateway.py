from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.cash_dto import CashSessionSnapshot, CreditSnapshot
from app.infrastructure.persistence.models.purchasing.expense import Expense
from app.infrastructure.persistence.models.sales.cash_session import CashSession, CashSessionStatus
from app.infrastructure.persistence.models.sales.credit import Credit, CreditStatus
from app.infrastructure.persistence.models.sales.customer import Customer
from app.infrastructure.persistence.models.sales.loyalty import LoyaltyConfig, LoyaltyTransaction
from app.infrastructure.persistence.models.sales.payment import Payment
from app.infrastructure.persistence.models.sales.sale import Sale, SaleStatus


class SqlAlchemyCashSessions:
    """Adaptador SQLAlchemy del puerto CashSessionStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self, tenant_id: int, user_id: int) -> CashSessionSnapshot | None:
        result = await self.db.execute(
            select(CashSession)
            .where(
                CashSession.tenant_id == tenant_id,
                CashSession.user_id == user_id,
                CashSession.status == CashSessionStatus.OPEN.value,
            )
            .with_for_update()
        )
        session = result.scalar_one_or_none()
        return CashSessionSnapshot(session.id, session.opening_balance) if session else None

    async def open(
        self, tenant_id: int, user_id: int, opening_balance: Decimal, notes: str | None
    ) -> int:
        session = CashSession(
            tenant_id=tenant_id,
            user_id=user_id,
            opening_balance=opening_balance,
            status=CashSessionStatus.OPEN.value,
            opened_at=datetime.utcnow(),
            notes=notes,
        )
        self.db.add(session)
        await self.db.flush()
        return session.id

    async def cash_sales_total(self, session_id: int) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Sale.total_amount), 0)).where(
                Sale.cash_session_id == session_id,
                Sale.status == SaleStatus.COMPLETED.value,
                Sale.payment_method == "cash",
            )
        )
        return Decimal(result.scalar() or 0)

    async def expenses_total(self, session_id: int) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.cash_session_id == session_id)
        )
        return Decimal(result.scalar() or 0)

    async def close(self, session_id: int, expected: Decimal, closing: Decimal) -> None:
        session = await self.db.get(CashSession, session_id)
        session.expected_balance = expected
        session.closing_balance = closing
        session.status = CashSessionStatus.CLOSED.value
        session.closed_at = datetime.utcnow()
        await self.db.flush()


class SqlAlchemyCreditPayments:
    """Adaptador SQLAlchemy del puerto CreditPaymentStore (bloquea el crédito contra abonos concurrentes)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_credit(self, tenant_id: int, credit_id: int) -> CreditSnapshot | None:
        result = await self.db.execute(
            select(Credit)
            .where(Credit.id == credit_id, Credit.tenant_id == tenant_id)
            .with_for_update()
        )
        credit = result.scalar_one_or_none()
        if not credit:
            return None
        return CreditSnapshot(
            credit.id, credit.customer_id,
            str(getattr(credit.status, "value", credit.status)), credit.remaining_amount,
        )

    async def register(
        self,
        tenant_id: int,
        credit_id: int,
        customer_id: int,
        amount: Decimal,
        new_remaining: Decimal,
        payment_method: str,
        notes: str | None,
    ) -> int:
        payment = Payment(
            tenant_id=tenant_id, credit_id=credit_id, amount=amount,
            payment_method=payment_method, notes=notes,
        )
        self.db.add(payment)

        credit = await self.db.get(Credit, credit_id)
        credit.remaining_amount = new_remaining
        if new_remaining <= 0:
            credit.status = CreditStatus.PAID

        customer = (
            await self.db.execute(
                select(Customer)
                .where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
                .with_for_update()
            )
        ).scalar_one()
        customer.current_balance -= amount
        await self.db.flush()
        return payment.id


class SqlAlchemyLoyaltyAdmin:
    """Adaptador SQLAlchemy del puerto LoyaltyAdmin."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_config(self, tenant_id: int, changes: dict) -> None:
        result = await self.db.execute(select(LoyaltyConfig).where(LoyaltyConfig.tenant_id == tenant_id))
        config = result.scalar_one_or_none()
        if not config:
            config = LoyaltyConfig(tenant_id=tenant_id)
            self.db.add(config)
        for field, value in changes.items():
            setattr(config, field, value)
        await self.db.flush()

    async def _customer(self, tenant_id: int, customer_id: int) -> Customer | None:
        result = await self.db.execute(
            select(Customer)
            .where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def customer_points(self, tenant_id: int, customer_id: int) -> int | None:
        customer = await self._customer(tenant_id, customer_id)
        return (customer.loyalty_points or 0) if customer else None

    async def adjust_points(
        self, tenant_id: int, customer_id: int, delta: int, description: str | None, sale_id: int | None
    ) -> int:
        customer = await self._customer(tenant_id, customer_id)
        customer.loyalty_points = (customer.loyalty_points or 0) + delta
        transaction = LoyaltyTransaction(
            tenant_id=tenant_id,
            customer_id=customer_id,
            sale_id=sale_id,
            points=delta,
            description=description,
            transaction_type="adjust",
        )
        self.db.add(transaction)
        await self.db.flush()
        return transaction.id
