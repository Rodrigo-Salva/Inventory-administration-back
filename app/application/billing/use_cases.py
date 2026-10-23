import logging

from app.application.billing.dto import CheckoutResult, CreateCheckoutCommand, PaymentNotification
from app.application.billing.ports import PaymentGateway, PlanCatalog, SubscriptionStore
from app.application.shared.ports import UnitOfWork
from app.domain.billing import rules

logger = logging.getLogger(__name__)


class CreateCheckout:
    """Crea la preferencia de pago con el precio definido por el servidor."""

    def __init__(self, gateway: PaymentGateway, catalog: PlanCatalog):
        self.gateway = gateway
        self.catalog = catalog

    async def execute(self, cmd: CreateCheckoutCommand) -> CheckoutResult:
        price = rules.resolve_price(
            cmd.plan, self.catalog.price_for(cmd.plan), cmd.client_price, self.catalog.strict
        )
        return await self.gateway.create_checkout(cmd.tenant_id, cmd.plan, price)


class ActivateSubscription:
    """Procesa la notificación de pago: verifica con el proveedor y renueva una sola vez por pago."""

    def __init__(
        self,
        gateway: PaymentGateway,
        catalog: PlanCatalog,
        subscriptions: SubscriptionStore,
        uow: UnitOfWork,
    ):
        self.gateway = gateway
        self.catalog = catalog
        self.subscriptions = subscriptions
        self.uow = uow

    async def execute(self, notification: PaymentNotification) -> bool:
        """True si se renovó una suscripción; False si se ignoró (no es pago aprobado, repetido, etc.)."""
        if notification.topic != "payment" or not notification.payment_id:
            return False
        payment = await self.gateway.fetch_payment(notification.payment_id)
        if not payment or payment.status != "approved":
            return False
        tenant_id = rules.parse_tenant_reference(payment.external_reference)
        if tenant_id is None:
            return False

        plan = payment.plan or rules.DEFAULT_PLAN
        expected = self.catalog.price_for(plan)
        if expected is not None and payment.amount < expected:
            logger.warning("Pago %s por %s menor al plan %s (%s)", notification.payment_id, payment.amount, plan, expected)
            return False

        try:
            subscription = await self.subscriptions.get_subscription(tenant_id)
            if not subscription:
                return False
            if not await self.subscriptions.register_payment_once(notification.payment_id, tenant_id):
                return False
            await self.subscriptions.renew(tenant_id, plan, rules.next_expiry(subscription.expires_at))
            await self.uow.commit()
            return True
        except Exception:
            await self.uow.rollback()
            raise
