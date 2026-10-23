import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.application.billing.dto import (
    CheckoutResult,
    CreateCheckoutCommand,
    PaymentInfo,
    PaymentNotification,
    TenantSubscription,
)
from app.application.billing.use_cases import ActivateSubscription, CreateCheckout
from app.domain.billing import rules
from app.domain.billing.errors import PlanNotConfiguredError

D = Decimal
NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


class Catalog:
    def __init__(self, prices=None, strict=False):
        self.prices, self._strict = prices or {}, strict

    def price_for(self, plan):
        return self.prices.get(plan)

    @property
    def strict(self):
        return self._strict


class World:
    def __init__(self, payment=None, expires_at=None, tenant=True):
        self.payment, self.expires_at, self.tenant = payment, expires_at, tenant
        self.seen = set()
        self.renewed = None
        self.checkout = None
        self.commits = self.rollbacks = 0

    async def create_checkout(self, tenant_id, plan, price):
        self.checkout = (tenant_id, plan, price)
        return CheckoutResult("pref-1", "http://pay", None)

    async def fetch_payment(self, payment_id):
        return self.payment

    async def register_payment_once(self, payment_id, tenant_id):
        if payment_id in self.seen:
            return False
        self.seen.add(payment_id)
        return True

    async def get_subscription(self, tenant_id):
        return TenantSubscription(tenant_id, self.expires_at) if self.tenant else None

    async def renew(self, tenant_id, plan, expires_at):
        self.renewed = (tenant_id, plan, expires_at)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def approved(amount="50", reference="tenant_7", plan=None):
    return PaymentInfo("approved", reference, D(amount), plan)


def note(payment_id="pay-1", topic="payment"):
    return PaymentNotification(topic, payment_id)


def test_price_is_defined_by_server():
    assert rules.resolve_price("premium", D("49.9"), D("0.01"), strict=True) == D("49.9")
    assert rules.resolve_price("premium", None, D("10"), strict=False) == D("10")
    with pytest.raises(PlanNotConfiguredError):
        rules.resolve_price("premium", None, D("10"), strict=True)
    with pytest.raises(PlanNotConfiguredError):
        rules.resolve_price("premium", None, None, strict=False)


def test_reference_and_expiry_rules():
    assert rules.parse_tenant_reference("tenant_12") == 12
    assert rules.parse_tenant_reference("tenant_x") is None and rules.parse_tenant_reference(None) is None
    assert rules.next_expiry(None, NOW) == NOW + timedelta(days=30)
    assert rules.next_expiry(NOW + timedelta(days=5), NOW) == NOW + timedelta(days=35)  # suma al vigente
    assert rules.next_expiry(NOW - timedelta(days=90), NOW) == NOW + timedelta(days=30)  # vencida: desde hoy


def test_webhook_signature():
    manifest = "id:abc123;request-id:req-1;ts:1700;"
    good = hmac.new(b"secret", manifest.encode(), hashlib.sha256).hexdigest()
    header = f"ts=1700,v1={good}"
    assert rules.valid_webhook_signature("secret", header, "req-1", "ABC123")
    assert not rules.valid_webhook_signature("other", header, "req-1", "abc123")
    assert not rules.valid_webhook_signature("secret", header, "req-2", "abc123")
    assert not rules.valid_webhook_signature("secret", None, "req-1", "abc123")
    assert not rules.valid_webhook_signature("secret", "garbage", "req-1", "abc123")


async def test_checkout_uses_catalog_price_over_client_price():
    w = World()
    result = await CreateCheckout(w, Catalog({"premium": D("49.9")}, strict=True)).execute(
        CreateCheckoutCommand(1, "premium", D("0.01"))
    )
    assert result.preference_id == "pref-1" and w.checkout == (1, "premium", D("49.9"))
    with pytest.raises(PlanNotConfiguredError):
        await CreateCheckout(w, Catalog(strict=True)).execute(CreateCheckoutCommand(1, "premium", D("0.01")))


async def test_payment_renews_once_even_if_notification_repeats():
    w = World(payment=approved(), expires_at=None)
    uc = ActivateSubscription(w, Catalog(), w, w)
    assert await uc.execute(note()) is True
    assert w.renewed[0:2] == (7, "premium") and w.commits == 1
    w.renewed = None
    assert await uc.execute(note()) is False  # reintento de MP: no renueva otra vez
    assert w.renewed is None and w.commits == 1


async def test_payment_ignored_when_invalid():
    cases = [
        (World(payment=None), note()),
        (World(payment=PaymentInfo("pending", "tenant_7", D("50"))), note()),
        (World(payment=approved(reference="otro")), note()),
        (World(payment=approved(), tenant=False), note()),
        (World(payment=approved()), note(topic="merchant_order")),
        (World(payment=approved()), PaymentNotification("payment", None)),
    ]
    for world, notification in cases:
        assert await ActivateSubscription(world, Catalog(), world, world).execute(notification) is False
        assert world.renewed is None


async def test_underpaid_plan_is_rejected():
    w = World(payment=approved(amount="1"))
    uc = ActivateSubscription(w, Catalog({"premium": D("49.9")}), w, w)
    assert await uc.execute(note()) is False and w.renewed is None and not w.seen
