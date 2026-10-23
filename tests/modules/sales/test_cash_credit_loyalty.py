from decimal import Decimal

import pytest

from app.application.sales.cash_dto import (
    AdjustLoyaltyPointsCommand,
    CashSessionSnapshot,
    CloseCashSessionCommand,
    CreditSnapshot,
    OpenCashSessionCommand,
    RegisterCreditPaymentCommand,
    UpdateLoyaltyConfigCommand,
)
from app.application.sales.cash_use_cases import (
    AdjustLoyaltyPoints,
    CloseCashSession,
    OpenCashSession,
    RegisterCreditPayment,
    UpdateLoyaltyConfig,
)
from app.domain.sales import rules
from app.domain.sales.errors import (
    CashSessionAlreadyOpenError,
    CreditAlreadyPaidError,
    CreditNotFoundError,
    CustomerNotFoundError,
    InvalidCashAmountError,
    InvalidLoyaltyAdjustmentError,
    InvalidLoyaltyConfigError,
    InvalidPaymentError,
    NoOpenCashSessionError,
    PaymentExceedsBalanceError,
)

D = Decimal


class World:
    def __init__(self, session=None, credit=None, points=None, cash_sales=D(0), expenses=D(0)):
        self.session, self.credit, self.points = session, credit, points
        self.cash_sales, self.expenses = cash_sales, expenses
        self.opened = self.closed = self.payment = self.adjusted = self.config = None
        self.commits = self.rollbacks = 0

    # CashSessionStore
    async def get_active(self, tenant_id, user_id):
        return self.session

    async def open(self, tenant_id, user_id, opening_balance, notes):
        self.opened = opening_balance
        return 5

    async def cash_sales_total(self, session_id):
        return self.cash_sales

    async def expenses_total(self, session_id):
        return self.expenses

    async def close(self, session_id, expected, closing):
        self.closed = (expected, closing)

    # CreditPaymentStore
    async def get_credit(self, tenant_id, credit_id):
        return self.credit

    async def register(self, tenant_id, credit_id, customer_id, amount, new_remaining, payment_method, notes):
        self.payment = (amount, new_remaining, payment_method)
        return 9

    # LoyaltyAdmin
    async def update_config(self, tenant_id, changes):
        self.config = changes

    async def customer_points(self, tenant_id, customer_id):
        return self.points

    async def adjust_points(self, tenant_id, customer_id, delta, description, sale_id):
        self.adjusted = delta
        return 3

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def test_rules():
    assert rules.expected_cash_balance(D(100), D(250), D(40)) == D(310)
    assert rules.apply_credit_payment(D(100), D(30)) == D(70)
    for bad in (D(0), D(-5)):
        with pytest.raises(InvalidPaymentError):
            rules.apply_credit_payment(D(100), bad)
    with pytest.raises(PaymentExceedsBalanceError):
        rules.apply_credit_payment(D(100), D(100.01))
    with pytest.raises(InvalidLoyaltyConfigError):
        rules.validate_loyalty_config({"amount_per_point": D(-1)})
    with pytest.raises(InvalidLoyaltyConfigError):
        rules.validate_loyalty_config({"min_redemption_points": -1})


async def test_open_session():
    w = World()
    assert await OpenCashSession(w, w).execute(OpenCashSessionCommand(1, 2, D(100))) == 5
    assert w.opened == D(100) and w.commits == 1

    w = World(session=CashSessionSnapshot(1, D(0)))
    with pytest.raises(CashSessionAlreadyOpenError):
        await OpenCashSession(w, w).execute(OpenCashSessionCommand(1, 2, D(100)))
    with pytest.raises(InvalidCashAmountError):
        await OpenCashSession(World(), World()).execute(OpenCashSessionCommand(1, 2, D(-1)))


async def test_close_session_computes_expected_cash():
    w = World(session=CashSessionSnapshot(7, D(100)), cash_sales=D(250), expenses=D(40))
    assert await CloseCashSession(w, w).execute(CloseCashSessionCommand(1, 2, D(305))) == 7
    assert w.closed == (D(310), D(305)) and w.commits == 1


async def test_close_session_requires_open_session():
    w = World()
    with pytest.raises(NoOpenCashSessionError):
        await CloseCashSession(w, w).execute(CloseCashSessionCommand(1, 2, D(0)))
    assert w.rollbacks == 1


async def test_credit_payment():
    w = World(credit=CreditSnapshot(1, 8, "pending", D(100)))
    await RegisterCreditPayment(w, w).execute(RegisterCreditPaymentCommand(1, 1, D(40), "cash"))
    assert w.payment == (D(40), D(60), "cash") and w.commits == 1


async def test_credit_payment_rejections():
    with pytest.raises(CreditNotFoundError):
        await RegisterCreditPayment(World(), World()).execute(RegisterCreditPaymentCommand(1, 1, D(5), "cash"))
    paid = World(credit=CreditSnapshot(1, 8, "paid", D(0)))
    with pytest.raises(CreditAlreadyPaidError):
        await RegisterCreditPayment(paid, paid).execute(RegisterCreditPaymentCommand(1, 1, D(5), "cash"))
    w = World(credit=CreditSnapshot(1, 8, "pending", D(100)))
    with pytest.raises(InvalidPaymentError):  # abono negativo aumentaría la deuda
        await RegisterCreditPayment(w, w).execute(RegisterCreditPaymentCommand(1, 1, D(-50), "cash"))
    with pytest.raises(PaymentExceedsBalanceError):
        await RegisterCreditPayment(w, w).execute(RegisterCreditPaymentCommand(1, 1, D(500), "cash"))
    assert w.payment is None


async def test_loyalty_config_and_adjustments():
    w = World(points=10)
    await UpdateLoyaltyConfig(w, w).execute(UpdateLoyaltyConfigCommand(1, {"amount_per_point": D(2)}))
    assert w.config == {"amount_per_point": D(2)}
    with pytest.raises(InvalidLoyaltyConfigError):
        await UpdateLoyaltyConfig(w, w).execute(UpdateLoyaltyConfigCommand(1, {"points_per_amount": D(0)}))

    assert await AdjustLoyaltyPoints(w, w).execute(AdjustLoyaltyPointsCommand(1, 4, -5)) == 3
    assert w.adjusted == -5
    with pytest.raises(InvalidLoyaltyAdjustmentError):
        await AdjustLoyaltyPoints(w, w).execute(AdjustLoyaltyPointsCommand(1, 4, -11))
    with pytest.raises(InvalidLoyaltyAdjustmentError):
        await AdjustLoyaltyPoints(w, w).execute(AdjustLoyaltyPointsCommand(1, 4, 0))
    with pytest.raises(CustomerNotFoundError):
        await AdjustLoyaltyPoints(World(points=None), World()).execute(AdjustLoyaltyPointsCommand(1, 4, 5))
