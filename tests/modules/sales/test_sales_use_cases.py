from decimal import Decimal

import pytest

from app.application.sales.dto import (
    AnnulSaleCommand,
    BatchStock,
    CreateSaleCommand,
    LoyaltyProgram,
    ProductStock,
    SaleLine,
    SaleSnapshot,
    SoldItem,
)
from app.application.sales.use_cases import AnnulSale, CreateSale
from app.domain.inventory.errors import (
    BatchNotFoundError,
    InsufficientStockError,
    ProductNotFoundError,
)
from app.domain.sales import rules
from app.domain.sales.errors import (
    CreditCustomerRequiredError,
    InsufficientCreditError,
    InsufficientLoyaltyPointsError,
    LoyaltyMinimumNotMetError,
    SaleAlreadyAnnulledError,
    SaleNotFoundError,
)


class World:
    """Doble en memoria que implementa los cuatro puertos y el UnitOfWork."""

    def __init__(self, products=None, batches=None, program=None, points=None, credit_ok=True):
        self.products = products or {}  # id -> [name, stock]
        self.batches = batches or {}  # id -> [number, qty]
        self.program = program
        self.points = points or {}  # customer_id -> points
        self.credit_ok = credit_ok
        self.items, self.exits, self.entries = [], [], []
        self.final = None
        self.credit_opened = None
        self.earned = self.redeemed = None
        self.annulled = False
        self.credit_annulled = self.loyalty_reversed = False
        self.snapshot = None
        self.commits = self.rollbacks = 0

    # SaleStore
    async def create(self, tenant_id, user_id, payment_method, notes, cash_session_id=None, branch_id=None):
        self.cash_session_id = cash_session_id
        self.sale_branch = branch_id
        return 99

    async def add_item(self, sale_id, line, subtotal):
        self.items.append((line.product_id, subtotal))

    async def finalize(self, sale_id, total, customer_id, redeemed_points, points_discount):
        self.final = (total, customer_id, redeemed_points, points_discount)

    async def get_for_annulment(self, sale_id, tenant_id):
        return self.snapshot

    async def mark_annulled(self, sale_id):
        self.annulled = True

    # InventoryPort
    async def get_product(self, tenant_id, product_id, branch_id=None):
        p = self.products.get(product_id)
        return ProductStock(product_id, p[0], p[1]) if p else None

    async def get_batch(self, tenant_id, batch_id):
        b = self.batches.get(batch_id)
        return BatchStock(batch_id, b[0], b[1]) if b else None

    async def register_sale_exit(self, tenant_id, user_id, sale_id, product_id, batch_id, quantity, branch_id=None):
        self.exit_branch = branch_id
        self.products[product_id][1] -= quantity
        if batch_id:
            self.batches[batch_id][1] -= quantity
        self.exits.append((product_id, batch_id, quantity))

    async def register_annulment_entry(self, tenant_id, user_id, sale_id, product_id, batch_id, quantity, branch_id=None):
        self.entry_branch = branch_id
        self.entries.append((product_id, batch_id, quantity))

    # LoyaltyPort
    async def get_active_program(self, tenant_id):
        return self.program

    async def get_points(self, tenant_id, customer_id):
        return self.points.get(customer_id)

    async def redeem(self, tenant_id, customer_id, sale_id, points):
        self.redeemed = points

    async def earn(self, tenant_id, customer_id, sale_id, points):
        self.earned = points

    async def reverse_for_sale(self, tenant_id, sale_id):
        self.loyalty_reversed = True

    # CreditPort
    async def has_available_credit(self, tenant_id, customer_id, amount):
        return self.credit_ok

    async def open_credit(self, tenant_id, customer_id, sale_id, amount):
        self.credit_opened = amount

    async def annul_for_sale(self, tenant_id, sale_id):
        self.credit_annulled = True

    # UnitOfWork
    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def create_sale(w: World) -> CreateSale:
    return CreateSale(w, w, w, w, w)


def annul_sale(w: World) -> AnnulSale:
    return AnnulSale(w, w, w, w, w)


def command(lines, **kw) -> CreateSaleCommand:
    return CreateSaleCommand(tenant_id=1, user_id=2, lines=tuple(lines), **kw)


PROGRAM = LoyaltyProgram(
    points_per_amount=Decimal("100"), amount_per_point=Decimal("10"), min_redemption_points=5
)


def test_rules():
    assert rules.line_subtotal(3, Decimal("2.50")) == Decimal("7.50")
    assert rules.redemption_discount(5, Decimal("10"), Decimal("30")) == Decimal("30")  # tope = total
    assert rules.earned_points(Decimal("250"), Decimal("100")) == 2
    assert rules.earned_points(Decimal("250"), Decimal("0")) == 0


async def test_simple_sale_discounts_stock_and_commits():
    w = World(products={1: ["Cafe", 10]})
    sale_id = await create_sale(w).execute(command([SaleLine(1, 3, Decimal("5"))]))
    assert sale_id == 99
    assert w.exits == [(1, None, 3)] and w.products[1][1] == 7
    assert w.final == (Decimal("15"), None, 0, Decimal("0"))
    assert (w.commits, w.rollbacks) == (1, 0)


async def test_product_not_found_rolls_back():
    w = World()
    with pytest.raises(ProductNotFoundError):
        await create_sale(w).execute(command([SaleLine(1, 1, Decimal("1"))]))
    assert (w.commits, w.rollbacks) == (0, 1)


async def test_insufficient_stock_message_and_rollback():
    w = World(products={1: ["Cafe", 2]})
    with pytest.raises(InsufficientStockError) as err:
        await create_sale(w).execute(command([SaleLine(1, 5, Decimal("1"))]))
    assert str(err.value) == "Stock insuficiente para 'Cafe'. Solicitado: 5, Disponible: 2"
    assert w.rollbacks == 1 and not w.exits


async def test_same_product_twice_checks_remaining_stock():
    w = World(products={1: ["Cafe", 5]})
    with pytest.raises(InsufficientStockError):
        await create_sale(w).execute(
            command([SaleLine(1, 3, Decimal("1")), SaleLine(1, 3, Decimal("1"))])
        )


async def test_batch_rules():
    w = World(products={1: ["Leche", 10]})
    with pytest.raises(BatchNotFoundError):
        await create_sale(w).execute(command([SaleLine(1, 1, Decimal("1"), batch_id=7)]))

    w = World(products={1: ["Leche", 10]}, batches={7: ["L-7", 1]})
    with pytest.raises(InsufficientStockError) as err:
        await create_sale(w).execute(command([SaleLine(1, 2, Decimal("1"), batch_id=7)]))
    assert "Lote: L-7" in str(err.value)

    w = World(products={1: ["Leche", 10]}, batches={7: ["L-7", 5]})
    await create_sale(w).execute(command([SaleLine(1, 2, Decimal("1"), batch_id=7)]))
    assert w.batches[7][1] == 3


async def test_redeem_points_applies_discount_and_earns_on_net_total():
    w = World(products={1: ["Cafe", 10]}, program=PROGRAM, points={5: 50})
    await create_sale(w).execute(
        command([SaleLine(1, 10, Decimal("100"))], customer_id=5, redeemed_points=10)
    )
    # total 1000 - (10 pts * 10) = 900 -> gana 9 puntos
    assert w.final == (Decimal("900"), 5, 10, Decimal("100"))
    assert w.redeemed == 10 and w.earned == 9


async def test_redeem_validations():
    w = World(products={1: ["Cafe", 10]}, program=PROGRAM, points={5: 3})
    with pytest.raises(InsufficientLoyaltyPointsError):
        await create_sale(w).execute(
            command([SaleLine(1, 1, Decimal("100"))], customer_id=5, redeemed_points=10)
        )
    w = World(products={1: ["Cafe", 10]}, program=PROGRAM, points={5: 50})
    with pytest.raises(LoyaltyMinimumNotMetError):
        await create_sale(w).execute(
            command([SaleLine(1, 1, Decimal("100"))], customer_id=5, redeemed_points=2)
        )


async def test_credit_sale():
    w = World(products={1: ["Cafe", 10]})
    with pytest.raises(CreditCustomerRequiredError):
        await create_sale(w).execute(command([SaleLine(1, 1, Decimal("10"))], payment_method="credit"))

    w = World(products={1: ["Cafe", 10]}, credit_ok=False)
    with pytest.raises(InsufficientCreditError):
        await create_sale(w).execute(
            command([SaleLine(1, 1, Decimal("10"))], payment_method="credit", customer_id=5)
        )

    w = World(products={1: ["Cafe", 10]})
    await create_sale(w).execute(
        command([SaleLine(1, 2, Decimal("10"))], payment_method="credit", customer_id=5)
    )
    assert w.credit_opened == Decimal("20")


async def test_annul_reverts_everything():
    w = World()
    w.snapshot = SaleSnapshot(99, "completed", (SoldItem(1, 3, None), SoldItem(2, 1, 7)))
    await annul_sale(w).execute(AnnulSaleCommand(99, 1, 2))
    assert w.entries == [(1, None, 3), (2, 7, 1)]
    assert w.annulled and w.credit_annulled and w.loyalty_reversed
    assert w.commits == 1


async def test_annul_errors():
    w = World()
    with pytest.raises(SaleNotFoundError):
        await annul_sale(w).execute(AnnulSaleCommand(99, 1, 2))
    w.snapshot = SaleSnapshot(99, "annulled", ())
    with pytest.raises(SaleAlreadyAnnulledError):
        await annul_sale(w).execute(AnnulSaleCommand(99, 1, 2))
    assert w.rollbacks == 2 and not w.entries


async def test_sale_is_attached_to_the_sellers_open_cash_session():
    from app.application.sales.cash_dto import CashSessionSnapshot

    class Sessions:
        async def get_active(self, tenant_id, user_id):
            return CashSessionSnapshot(42, Decimal(0))

    w = World(products={1: ["Cafe", 10]})
    await CreateSale(w, w, w, w, w, cash_sessions=Sessions()).execute(command([SaleLine(1, 1, Decimal("5"))]))
    assert w.cash_session_id == 42

    w = World(products={1: ["Cafe", 10]})
    await create_sale(w).execute(command([SaleLine(1, 1, Decimal("5"))]))  # sin sesiones: sigue funcionando
    assert w.cash_session_id is None


class FakeBranches:
    """BranchResolver: sin sucursal pedida usa la 7 (la del vendedor)."""

    async def resolve(self, tenant_id, user_id, requested_branch_id=None):
        return requested_branch_id or 7


async def test_sale_is_dispatched_from_the_resolved_branch():
    w = World(products={1: ["Cafe", 10]})
    await CreateSale(w, w, w, w, w, branches=FakeBranches()).execute(command([SaleLine(1, 2, Decimal("5"))]))
    assert w.sale_branch == 7 and w.exit_branch == 7

    w = World(products={1: ["Cafe", 10]})
    await CreateSale(w, w, w, w, w, branches=FakeBranches()).execute(command([SaleLine(1, 2, Decimal("5"))], branch_id=3))
    assert w.sale_branch == 3 and w.exit_branch == 3


async def test_annulment_returns_stock_to_the_branch_of_the_sale():
    w = World()
    w.snapshot = SaleSnapshot(99, "completed", (SoldItem(1, 3, None),), branch_id=5)
    await annul_sale(w).execute(AnnulSaleCommand(99, 1, 2))
    assert w.entry_branch == 5
