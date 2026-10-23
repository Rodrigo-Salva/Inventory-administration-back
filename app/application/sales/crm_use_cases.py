from decimal import Decimal

from app.application.sales.crm_dto import (
    ConvertQuoteCommand,
    CreateCustomerCommand,
    CreateQuoteCommand,
    DeleteCustomerCommand,
    UpdateCustomerCommand,
)
from app.application.sales.crm_ports import CustomerStore, QuoteStore
from app.application.sales.dto import CreateSaleCommand, SaleLine
from app.application.sales.use_cases import CreateSale
from app.application.shared.ports import TenantResources, UnitOfWork
from app.domain.inventory.errors import ProductNotFoundError
from app.domain.sales.errors import (
    CreditManagementForbiddenError,
    CustomerNotFoundError,
    DuplicateCustomerError,
    InvalidCreditLimitError,
    InvalidQuoteError,
    QuoteNotConvertibleError,
    QuoteNotFoundError,
)
from app.domain.shared.errors import DomainError

QUOTE_CONVERTED = "converted"
QUOTE_REJECTED = "rejected"


def _check_credit_limit(value, current, can_manage: bool) -> None:
    """El límite de crédito solo lo cambia quien tiene 'credits:manage' y nunca puede ser negativo."""
    if value is None:
        return
    if value < 0:
        raise InvalidCreditLimitError()
    if value != current and not can_manage:
        raise CreditManagementForbiddenError()


class CreateCustomer:
    def __init__(self, customers: CustomerStore, uow: UnitOfWork):
        self.customers = customers
        self.uow = uow

    async def execute(self, cmd: CreateCustomerCommand) -> int:
        try:
            attrs = {k: v for k, v in cmd.attributes.items() if k != "current_balance"}  # lo gestiona el sistema
            _check_credit_limit(attrs.get("credit_limit"), Decimal(0), cmd.can_manage_credit)
            document = attrs.get("document_number")
            if document and await self.customers.find_by_document(cmd.tenant_id, document):
                raise DuplicateCustomerError(document)
            customer_id = await self.customers.create(cmd.tenant_id, attrs)
            await self.uow.commit()
            return customer_id
        except Exception:
            await self.uow.rollback()
            raise


class UpdateCustomer:
    def __init__(self, customers: CustomerStore, uow: UnitOfWork):
        self.customers = customers
        self.uow = uow

    async def execute(self, cmd: UpdateCustomerCommand) -> int:
        try:
            customer = await self.customers.get(cmd.tenant_id, cmd.customer_id)
            if not customer:
                raise CustomerNotFoundError()
            changes = {k: v for k, v in cmd.changes.items() if k != "current_balance"}
            _check_credit_limit(changes.get("credit_limit"), customer.credit_limit, cmd.can_manage_credit)
            document = changes.get("document_number")
            if document and document != customer.document_number:
                existing = await self.customers.find_by_document(cmd.tenant_id, document)
                if existing and existing.id != customer.id:
                    raise DuplicateCustomerError(document)
            if changes:
                await self.customers.update(cmd.tenant_id, customer.id, changes)
            await self.uow.commit()
            return customer.id
        except Exception:
            await self.uow.rollback()
            raise


class DeleteCustomer:
    def __init__(self, customers: CustomerStore, uow: UnitOfWork):
        self.customers = customers
        self.uow = uow

    async def execute(self, cmd: DeleteCustomerCommand) -> None:
        try:
            customer = await self.customers.get(cmd.tenant_id, cmd.customer_id)
            if not customer:
                raise CustomerNotFoundError()
            if customer.current_balance != 0:
                raise DomainError("El cliente tiene saldo pendiente; salde su crédito antes de eliminarlo")
            await self.customers.soft_delete(cmd.tenant_id, customer.id)
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            raise


class CreateQuote:
    def __init__(self, quotes: QuoteStore, resources: TenantResources, uow: UnitOfWork):
        self.quotes = quotes
        self.resources = resources
        self.uow = uow

    async def execute(self, cmd: CreateQuoteCommand) -> int:
        try:
            if not cmd.lines:
                raise InvalidQuoteError("La cotización debe tener al menos un ítem")
            if cmd.customer_id and not await self.resources.customer_exists(cmd.tenant_id, cmd.customer_id):
                raise CustomerNotFoundError()
            missing = await self.resources.missing_products(cmd.tenant_id, {i.product_id for i in cmd.lines})
            if missing:
                raise ProductNotFoundError(sorted(missing)[0])
            total = sum((Decimal(i.quantity) * i.unit_price for i in cmd.lines), Decimal(0))
            quote_id = await self.quotes.create(cmd, total)
            await self.uow.commit()
            return quote_id
        except Exception:
            await self.uow.rollback()
            raise


class ConvertQuote:
    """Convierte la cotización en venta y la marca convertida en UNA sola transacción."""

    def __init__(self, quotes: QuoteStore, create_sale: CreateSale, uow: UnitOfWork):
        self.quotes = quotes
        self.create_sale = create_sale
        self.uow = uow

    async def execute(self, cmd: ConvertQuoteCommand) -> int:
        try:
            quote = await self.quotes.get_for_update(cmd.tenant_id, cmd.quote_id)
            if not quote:
                raise QuoteNotFoundError()
            if quote.status == QUOTE_CONVERTED:
                raise QuoteNotConvertibleError("La cotización ya fue convertida a venta")
            if quote.status == QUOTE_REJECTED:
                raise QuoteNotConvertibleError("No se puede convertir una cotización rechazada")

            sale_id = await self.create_sale.register(
                CreateSaleCommand(
                    tenant_id=cmd.tenant_id,
                    user_id=cmd.user_id,
                    lines=tuple(SaleLine(i.product_id, i.quantity, i.unit_price) for i in quote.lines),
                    payment_method=cmd.payment_method,
                    notes=f"Generada desde la Cotización #{quote.id}. {quote.notes or ''}".strip(),
                    customer_id=quote.customer_id,
                )
            )
            await self.quotes.mark_converted(quote.id, sale_id)
            await self.uow.commit()
            return sale_id
        except Exception:
            await self.uow.rollback()
            raise
