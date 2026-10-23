from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.sales.crm_dto import CreateQuoteCommand, CustomerRef, QuoteLine, QuoteSnapshot
from app.domain.sales.errors import DuplicateCustomerError
from app.infrastructure.persistence.models.sales.customer import Customer
from app.infrastructure.persistence.models.sales.quote import Quote, QuoteItem, QuoteStatus
from app.infrastructure.persistence.repositories.sales.customer_repo import CustomerRepository


class SqlAlchemyCustomerStore:
    """Adaptador SQLAlchemy del puerto CustomerStore."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CustomerRepository(db)

    @staticmethod
    def _ref(customer) -> CustomerRef | None:
        if not customer:
            return None
        return CustomerRef(
            customer.id, customer.document_number,
            Decimal(customer.credit_limit or 0), Decimal(customer.current_balance or 0),
        )

    async def get(self, tenant_id: int, customer_id: int) -> CustomerRef | None:
        result = await self.db.execute(
            select(Customer)
            .where(Customer.id == customer_id, Customer.tenant_id == tenant_id, Customer.is_deleted == False)  # noqa: E712
            .with_for_update()
        )
        return self._ref(result.scalar_one_or_none())

    async def find_by_document(self, tenant_id: int, document_number: str) -> CustomerRef | None:
        return self._ref(await self.repo.get_by_document(document_number, tenant_id))

    async def create(self, tenant_id: int, attributes: dict[str, Any]) -> int:
        try:
            async with self.db.begin_nested():
                customer = await self.repo.create({**attributes, "tenant_id": tenant_id})
        except IntegrityError as error:
            raise DuplicateCustomerError(str(attributes.get("document_number"))) from error
        return customer.id

    async def update(self, tenant_id: int, customer_id: int, changes: dict[str, Any]) -> None:
        await self.repo.update(customer_id, changes, tenant_id)

    async def soft_delete(self, tenant_id: int, customer_id: int) -> None:
        await self.repo.delete(customer_id, tenant_id)


class SqlAlchemyQuoteStore:
    """Adaptador SQLAlchemy del puerto QuoteStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, command: CreateQuoteCommand, total: Decimal) -> int:
        quote = Quote(
            tenant_id=command.tenant_id,
            user_id=command.user_id,
            customer_id=command.customer_id,
            valid_until=command.valid_until,
            notes=command.notes,
            total_amount=total,
        )
        self.db.add(quote)
        await self.db.flush()
        for line in command.lines:
            self.db.add(
                QuoteItem(
                    quote_id=quote.id,
                    product_id=line.product_id,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    subtotal=Decimal(line.quantity) * line.unit_price,
                )
            )
        await self.db.flush()
        return quote.id

    async def get_for_update(self, tenant_id: int, quote_id: int) -> QuoteSnapshot | None:
        result = await self.db.execute(
            select(Quote)
            .options(selectinload(Quote.items))
            .where(Quote.id == quote_id, Quote.tenant_id == tenant_id)
            .with_for_update()
        )
        quote = result.scalar_one_or_none()
        if not quote:
            return None
        return QuoteSnapshot(
            id=quote.id,
            status=str(getattr(quote.status, "value", quote.status)),
            customer_id=quote.customer_id,
            notes=quote.notes,
            lines=tuple(QuoteLine(i.product_id, i.quantity, Decimal(i.unit_price)) for i in quote.items),
        )

    async def mark_converted(self, quote_id: int, sale_id: int) -> None:
        quote = await self.db.get(Quote, quote_id)
        quote.status = QuoteStatus.CONVERTED.value
        quote.sale_id = sale_id
        await self.db.flush()
