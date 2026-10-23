from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.dto import LoyaltyProgram
from app.infrastructure.persistence.models.sales.customer import Customer
from app.infrastructure.persistence.models.sales.loyalty import LoyaltyConfig, LoyaltyTransaction


class SqlAlchemyLoyalty:
    """Adaptador SQLAlchemy del puerto LoyaltyPort (todas las consultas filtran por tenant)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _customer(self, tenant_id: int, customer_id: int) -> Customer | None:
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_active_program(self, tenant_id: int) -> LoyaltyProgram | None:
        result = await self.db.execute(
            select(LoyaltyConfig).where(
                LoyaltyConfig.tenant_id == tenant_id, LoyaltyConfig.is_active == True  # noqa: E712
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            return None
        return LoyaltyProgram(
            points_per_amount=config.points_per_amount,
            amount_per_point=config.amount_per_point,
            min_redemption_points=config.min_redemption_points,
        )

    async def get_points(self, tenant_id: int, customer_id: int) -> int | None:
        customer = await self._customer(tenant_id, customer_id)
        return (customer.loyalty_points or 0) if customer else None

    async def redeem(self, tenant_id: int, customer_id: int, sale_id: int, points: int) -> None:
        customer = await self._customer(tenant_id, customer_id)
        customer.loyalty_points -= points
        self._record(tenant_id, customer.id, sale_id, -points, f"Puntos redimidos en venta #{sale_id}", "redeem")

    async def earn(self, tenant_id: int, customer_id: int, sale_id: int, points: int) -> None:
        customer = await self._customer(tenant_id, customer_id)
        if not customer:
            return
        customer.loyalty_points += points
        self._record(tenant_id, customer.id, sale_id, points, f"Puntos ganados por venta #{sale_id}", "earn")

    async def reverse_for_sale(self, tenant_id: int, sale_id: int) -> None:
        result = await self.db.execute(
            select(LoyaltyTransaction).where(
                LoyaltyTransaction.sale_id == sale_id,
                LoyaltyTransaction.tenant_id == tenant_id,
                LoyaltyTransaction.transaction_type.in_(("earn", "redeem")),
            )
        )
        for original in result.scalars().all():
            customer = await self._customer(tenant_id, original.customer_id)
            if not customer:
                continue
            delta = -original.points  # earn (+n) se descuenta; redeem (-n) se devuelve
            customer.loyalty_points += delta
            description = (
                f"Puntos revertidos por anulación de venta #{sale_id}"
                if original.transaction_type == "earn"
                else f"Puntos devueltos por anulación de venta #{sale_id}"
            )
            self._record(tenant_id, customer.id, sale_id, delta, description, "adjust")

    def _record(
        self, tenant_id: int, customer_id: int, sale_id: int, points: int, description: str, kind: str
    ) -> None:
        self.db.add(
            LoyaltyTransaction(
                tenant_id=tenant_id,
                customer_id=customer_id,
                sale_id=sale_id,
                points=points,
                description=description,
                transaction_type=kind,
            )
        )
