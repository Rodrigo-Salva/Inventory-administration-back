from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.application.billing.dto import CheckoutResult, PaymentInfo, TenantSubscription


class PaymentGateway(Protocol):
    async def create_checkout(self, tenant_id: int, plan: str, price: Decimal) -> CheckoutResult:
        """Lanza PaymentGatewayError si el proveedor rechaza o no responde."""
        ...

    async def fetch_payment(self, payment_id: str) -> PaymentInfo | None: ...


class PlanCatalog(Protocol):
    def price_for(self, plan: str) -> Decimal | None: ...

    @property
    def strict(self) -> bool:
        """True si el precio del cliente nunca debe aceptarse (producción)."""
        ...


class SubscriptionStore(Protocol):
    async def register_payment_once(self, payment_id: str, tenant_id: int) -> bool:
        """Registra el pago; devuelve False si ya había sido procesado (idempotencia)."""
        ...

    async def get_subscription(self, tenant_id: int) -> TenantSubscription | None: ...

    async def renew(self, tenant_id: int, plan: str, expires_at: datetime) -> None: ...
