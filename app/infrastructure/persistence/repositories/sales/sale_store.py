from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.sales.dto import SaleLine, SaleSnapshot, SoldItem
from app.infrastructure.persistence.models.sales.sale import Sale, SaleItem, SaleStatus


class SqlAlchemySaleStore:
    """Adaptador SQLAlchemy del puerto SaleStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        tenant_id: int,
        user_id: int,
        payment_method: str,
        notes: str | None,
        cash_session_id: int | None = None,
        branch_id: int | None = None,
    ) -> int:
        sale = Sale(
            cash_session_id=cash_session_id,
            branch_id=branch_id,
            tenant_id=tenant_id,
            user_id=user_id,
            payment_method=payment_method,
            notes=notes,
            total_amount=0,
        )
        self.db.add(sale)
        await self.db.flush()
        return sale.id

    async def add_item(self, sale_id: int, line: SaleLine, subtotal: Decimal) -> None:
        self.db.add(
            SaleItem(
                sale_id=sale_id,
                product_id=line.product_id,
                batch_id=line.batch_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                subtotal=subtotal,
            )
        )

    async def finalize(
        self,
        sale_id: int,
        total: Decimal,
        customer_id: int | None,
        redeemed_points: int,
        points_discount: Decimal,
    ) -> None:
        sale = await self.db.get(Sale, sale_id)
        sale.total_amount = total
        sale.customer_id = customer_id
        sale.redeemed_points = redeemed_points
        sale.points_discount_amount = points_discount
        await self.db.flush()

    async def get_for_annulment(self, sale_id: int, tenant_id: int) -> SaleSnapshot | None:
        result = await self.db.execute(
            select(Sale)
            .options(selectinload(Sale.items))
            .where(Sale.id == sale_id, Sale.tenant_id == tenant_id)
        )
        sale = result.scalar_one_or_none()
        if not sale:
            return None
        return SaleSnapshot(
            id=sale.id,
            status=str(getattr(sale.status, "value", sale.status)),
            items=tuple(SoldItem(i.product_id, i.quantity, i.batch_id) for i in sale.items),
            branch_id=sale.branch_id,
        )

    async def mark_annulled(self, sale_id: int) -> None:
        sale = await self.db.get(Sale, sale_id)
        sale.status = SaleStatus.ANNULLED.value
        await self.db.flush()
