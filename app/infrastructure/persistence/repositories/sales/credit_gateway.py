from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.sales.credit import Credit, CreditStatus
from app.infrastructure.persistence.models.sales.customer import Customer
from app.infrastructure.persistence.repositories.sales.credit_repo import CreditRepository


class SqlAlchemyCredit:
    """Adaptador SQLAlchemy del puerto CreditPort."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.credits = CreditRepository(db)

    async def has_available_credit(self, tenant_id: int, customer_id: int, amount: Decimal) -> bool:
        return await self.credits.check_credit_availability(tenant_id, customer_id, amount)

    async def open_credit(
        self, tenant_id: int, customer_id: int, sale_id: int, amount: Decimal
    ) -> None:
        await self.credits.create_from_sale(
            tenant_id=tenant_id, customer_id=customer_id, sale_id=sale_id, total_amount=amount
        )

    async def annul_for_sale(self, tenant_id: int, sale_id: int) -> None:
        result = await self.db.execute(
            select(Credit).where(Credit.sale_id == sale_id, Credit.tenant_id == tenant_id)
        )
        credit = result.scalar_one_or_none()
        if not credit or credit.status == CreditStatus.ANNULLED:
            return
        customer = (
            await self.db.execute(
                select(Customer).where(
                    Customer.id == credit.customer_id, Customer.tenant_id == tenant_id
                )
            )
        ).scalar_one()
        customer.current_balance -= credit.remaining_amount
        credit.status = CreditStatus.ANNULLED
        await self.db.flush()
