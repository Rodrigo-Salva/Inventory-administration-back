from datetime import date
from decimal import Decimal

import pytest

from app.application.sales.crm_dto import (
    ConvertQuoteCommand,
    CreateCustomerCommand,
    CreateQuoteCommand,
    CustomerRef,
    DeleteCustomerCommand,
    QuoteLine,
    QuoteSnapshot,
    UpdateCustomerCommand,
)
from app.application.sales.crm_use_cases import (
    ConvertQuote,
    CreateCustomer,
    CreateQuote,
    DeleteCustomer,
    UpdateCustomer,
)
from app.domain.inventory.errors import ProductNotFoundError
from app.domain.shared.errors import DomainError
from app.domain.sales.errors import (
    CreditManagementForbiddenError,
    CustomerNotFoundError,
    DuplicateCustomerError,
    InvalidCreditLimitError,
    InvalidQuoteError,
    QuoteNotConvertibleError,
    QuoteNotFoundError,
)

D = Decimal


class World:
    def __init__(self, customers=(), quote=None, products=(1,), fail_sale=False):
        self.customers = {c.id: c for c in customers}
        self.quote = quote
        self.products = set(products)
        self.fail_sale = fail_sale
        self.created = self.updated = self.deleted = self.quote_created = self.converted = None
        self.sale_cmd = None
        self.commits = self.rollbacks = 0

    # CustomerStore
    async def get(self, tenant_id, customer_id):
        return self.customers.get(customer_id)

    async def find_by_document(self, tenant_id, document_number):
        return next((c for c in self.customers.values() if c.document_number == document_number), None)

    async def create(self, *args):
        if isinstance(args[0], CreateQuoteCommand):  # QuoteStore.create(cmd, total)
            self.quote_created = args
            return 30
        self.created = args[1]  # CustomerStore.create(tenant, attrs)
        return 20

    async def update(self, tenant_id, customer_id, changes):
        self.updated = (customer_id, changes)

    async def soft_delete(self, tenant_id, customer_id):
        self.deleted = customer_id

    # QuoteStore
    async def get_for_update(self, tenant_id, quote_id):
        return self.quote

    async def mark_converted(self, quote_id, sale_id):
        self.converted = (quote_id, sale_id)

    # TenantResources
    async def customer_exists(self, tenant_id, customer_id):
        return customer_id in self.customers

    async def missing_products(self, tenant_id, ids):
        return set(ids) - self.products

    # CreateSale doble
    async def register(self, command):
        if self.fail_sale:
            raise DomainError("sin stock")
        self.sale_cmd = command
        return 99

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


CUSTOMER = CustomerRef(1, "DOC-1", D("100"), D(0))


async def test_create_customer_ignores_balance_and_gates_credit_limit():
    w = World()
    await CreateCustomer(w, w).execute(
        CreateCustomerCommand(1, {"name": "Ana", "current_balance": D("-500"), "credit_limit": D(0)})
    )
    assert "current_balance" not in w.created  # el cliente no puede fijarse el saldo deudor

    with pytest.raises(CreditManagementForbiddenError):
        await CreateCustomer(w, w).execute(CreateCustomerCommand(1, {"name": "B", "credit_limit": D("1000")}))
    await CreateCustomer(w, w).execute(CreateCustomerCommand(1, {"name": "B", "credit_limit": D("1000")}, True))
    with pytest.raises(InvalidCreditLimitError):
        await CreateCustomer(w, w).execute(CreateCustomerCommand(1, {"name": "C", "credit_limit": D("-1")}, True))


async def test_create_customer_rejects_duplicate_document():
    w = World(customers=[CUSTOMER])
    with pytest.raises(DuplicateCustomerError) as err:
        await CreateCustomer(w, w).execute(CreateCustomerCommand(1, {"name": "X", "document_number": "DOC-1"}))
    assert str(err.value) == "Cliente con document_number='DOC-1' ya existe"


async def test_update_customer_credit_and_balance_rules():
    w = World(customers=[CUSTOMER])
    uc = UpdateCustomer(w, w)
    await uc.execute(UpdateCustomerCommand(1, 1, {"name": "N", "current_balance": D(0), "credit_limit": D("100")}))
    assert w.updated == (1, {"name": "N", "credit_limit": D("100")})  # mismo límite y sin saldo: permitido
    with pytest.raises(CreditManagementForbiddenError):
        await uc.execute(UpdateCustomerCommand(1, 1, {"credit_limit": D("9999")}))
    await uc.execute(UpdateCustomerCommand(1, 1, {"credit_limit": D("9999")}, can_manage_credit=True))
    with pytest.raises(CustomerNotFoundError):
        await uc.execute(UpdateCustomerCommand(1, 404, {"name": "x"}))
    other = CustomerRef(2, "DOC-2", D(0), D(0))
    w2 = World(customers=[CUSTOMER, other])
    with pytest.raises(DuplicateCustomerError):
        await UpdateCustomer(w2, w2).execute(UpdateCustomerCommand(1, 2, {"document_number": "DOC-1"}))


async def test_delete_customer_blocked_with_debt():
    w = World(customers=[CustomerRef(1, None, D(0), D("50"))])
    with pytest.raises(DomainError):
        await DeleteCustomer(w, w).execute(DeleteCustomerCommand(1, 1))
    w = World(customers=[CUSTOMER])
    await DeleteCustomer(w, w).execute(DeleteCustomerCommand(1, 1))
    assert w.deleted == 1


def quote_cmd(lines=None, **kw):
    lines = lines if lines is not None else [QuoteLine(1, 2, D("5.5"))]
    return CreateQuoteCommand(1, 2, date(2026, 12, 31), tuple(lines), **kw)


async def test_create_quote_validates_and_totals():
    w = World(customers=[CUSTOMER])
    assert await CreateQuote(w, w, w).execute(quote_cmd(customer_id=1)) == 30
    assert w.quote_created[1] == D("11.0")
    with pytest.raises(InvalidQuoteError):
        await CreateQuote(w, w, w).execute(quote_cmd(lines=[]))
    with pytest.raises(CustomerNotFoundError):
        await CreateQuote(w, w, w).execute(quote_cmd(customer_id=77))
    with pytest.raises(ProductNotFoundError):
        await CreateQuote(w, w, w).execute(quote_cmd(lines=[QuoteLine(99, 1, D(1))]))


def snapshot(status="pending"):
    return QuoteSnapshot(5, status, 1, "nota", (QuoteLine(1, 2, D("5")),))


async def test_convert_quote_is_one_transaction():
    w = World(quote=snapshot())
    sale_id = await ConvertQuote(w, w, w).execute(ConvertQuoteCommand(1, 2, 5, "card"))
    assert sale_id == 99 and w.converted == (5, 99) and w.commits == 1
    assert w.sale_cmd.payment_method == "card" and w.sale_cmd.customer_id == 1
    assert w.sale_cmd.notes.startswith("Generada desde la Cotización #5")


async def test_convert_quote_rejections_and_rollback_on_sale_failure():
    for status, message in (("converted", "ya fue convertida"), ("rejected", "rechazada")):
        w = World(quote=snapshot(status))
        with pytest.raises(QuoteNotConvertibleError, match=message):
            await ConvertQuote(w, w, w).execute(ConvertQuoteCommand(1, 2, 5))
        assert w.converted is None
    with pytest.raises(QuoteNotFoundError):
        await ConvertQuote(World(), World(), World()).execute(ConvertQuoteCommand(1, 2, 5))

    w = World(quote=snapshot(), fail_sale=True)  # si la venta falla, la cotización no queda marcada
    with pytest.raises(DomainError):
        await ConvertQuote(w, w, w).execute(ConvertQuoteCommand(1, 2, 5))
    assert w.converted is None and w.commits == 0 and w.rollbacks == 1
