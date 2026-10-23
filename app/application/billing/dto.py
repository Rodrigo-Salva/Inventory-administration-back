from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class CreateCheckoutCommand:
    tenant_id: int
    plan: str
    client_price: Decimal | None = None


@dataclass(frozen=True)
class CheckoutResult:
    preference_id: str | None
    init_point: str | None
    sandbox_init_point: str | None


@dataclass(frozen=True)
class PaymentInfo:
    status: str
    external_reference: str | None
    amount: Decimal
    plan: str | None = None


@dataclass(frozen=True)
class TenantSubscription:
    tenant_id: int
    expires_at: "datetime | None"


@dataclass(frozen=True)
class PaymentNotification:
    topic: str | None
    payment_id: str | None
