from app.application.sales.cash_dto import (
    AdjustLoyaltyPointsCommand,
    CloseCashSessionCommand,
    OpenCashSessionCommand,
    RegisterCreditPaymentCommand,
    UpdateLoyaltyConfigCommand,
)
from app.application.sales.cash_ports import CashSessionStore, CreditPaymentStore, LoyaltyAdmin
from app.application.shared.ports import UnitOfWork
from app.domain.sales import rules
from app.domain.sales.errors import (
    CashSessionAlreadyOpenError,
    CreditAlreadyPaidError,
    CreditNotFoundError,
    CustomerNotFoundError,
    NoOpenCashSessionError,
)

CREDIT_PAID = "paid"


class OpenCashSession:
    def __init__(self, sessions: CashSessionStore, uow: UnitOfWork):
        self.sessions = sessions
        self.uow = uow

    async def execute(self, cmd: OpenCashSessionCommand) -> int:
        try:
            rules.validate_cash_amount(cmd.opening_balance)
            if await self.sessions.get_active(cmd.tenant_id, cmd.user_id):
                raise CashSessionAlreadyOpenError()
            session_id = await self.sessions.open(
                cmd.tenant_id, cmd.user_id, cmd.opening_balance, cmd.notes
            )
            await self.uow.commit()
            return session_id
        except Exception:
            await self.uow.rollback()
            raise


class CloseCashSession:
    def __init__(self, sessions: CashSessionStore, uow: UnitOfWork):
        self.sessions = sessions
        self.uow = uow

    async def execute(self, cmd: CloseCashSessionCommand) -> int:
        try:
            rules.validate_cash_amount(cmd.closing_balance)
            session = await self.sessions.get_active(cmd.tenant_id, cmd.user_id)
            if not session:
                raise NoOpenCashSessionError()
            expected = rules.expected_cash_balance(
                session.opening_balance,
                await self.sessions.cash_sales_total(session.id),
                await self.sessions.expenses_total(session.id),
            )
            await self.sessions.close(session.id, expected, cmd.closing_balance)
            await self.uow.commit()
            return session.id
        except Exception:
            await self.uow.rollback()
            raise


class RegisterCreditPayment:
    """Abono a un crédito: actualiza saldo del crédito y del cliente en una transacción."""

    def __init__(self, payments: CreditPaymentStore, uow: UnitOfWork):
        self.payments = payments
        self.uow = uow

    async def execute(self, cmd: RegisterCreditPaymentCommand) -> int:
        try:
            credit = await self.payments.get_credit(cmd.tenant_id, cmd.credit_id)
            if not credit:
                raise CreditNotFoundError()
            if credit.status == CREDIT_PAID:
                raise CreditAlreadyPaidError()
            new_remaining = rules.apply_credit_payment(credit.remaining_amount, cmd.amount)
            payment_id = await self.payments.register(
                cmd.tenant_id, credit.id, credit.customer_id, cmd.amount,
                new_remaining, cmd.payment_method, cmd.notes,
            )
            await self.uow.commit()
            return payment_id
        except Exception:
            await self.uow.rollback()
            raise


class UpdateLoyaltyConfig:
    def __init__(self, loyalty: LoyaltyAdmin, uow: UnitOfWork):
        self.loyalty = loyalty
        self.uow = uow

    async def execute(self, cmd: UpdateLoyaltyConfigCommand) -> None:
        try:
            rules.validate_loyalty_config(cmd.changes)
            await self.loyalty.update_config(cmd.tenant_id, cmd.changes)
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            raise


class AdjustLoyaltyPoints:
    """Ajuste manual de puntos (siempre queda registrado como transacción 'adjust')."""

    def __init__(self, loyalty: LoyaltyAdmin, uow: UnitOfWork):
        self.loyalty = loyalty
        self.uow = uow

    async def execute(self, cmd: AdjustLoyaltyPointsCommand) -> int:
        try:
            current = await self.loyalty.customer_points(cmd.tenant_id, cmd.customer_id)
            if current is None:
                raise CustomerNotFoundError()
            rules.validate_loyalty_adjustment(current, cmd.points)
            transaction_id = await self.loyalty.adjust_points(
                cmd.tenant_id, cmd.customer_id, cmd.points, cmd.description, cmd.sale_id
            )
            await self.uow.commit()
            return transaction_id
        except Exception:
            await self.uow.rollback()
            raise
