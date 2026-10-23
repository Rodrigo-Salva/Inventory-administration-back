from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OpenCashSessionCommand:
    tenant_id: int
    user_id: int
    opening_balance: Decimal
    notes: str | None = None


@dataclass(frozen=True)
class CloseCashSessionCommand:
    tenant_id: int
    user_id: int
    closing_balance: Decimal


@dataclass(frozen=True)
class CashSessionSnapshot:
    id: int
    opening_balance: Decimal


@dataclass(frozen=True)
class RegisterCreditPaymentCommand:
    tenant_id: int
    credit_id: int
    amount: Decimal
    payment_method: str
    notes: str | None = None


@dataclass(frozen=True)
class CreditSnapshot:
    id: int
    customer_id: int
    status: str
    remaining_amount: Decimal


@dataclass(frozen=True)
class UpdateLoyaltyConfigCommand:
    tenant_id: int
    changes: dict


@dataclass(frozen=True)
class AdjustLoyaltyPointsCommand:
    tenant_id: int
    customer_id: int
    points: int
    description: str | None = None
    sale_id: int | None = None
