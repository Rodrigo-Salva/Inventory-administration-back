from decimal import Decimal

import pytest

from app.application.purchasing.dto import (
    CreatePurchaseCommand,
    PurchaseActionCommand,
    PurchaseItemInput,
    PurchaseSnapshot,
)
from app.application.purchasing.use_cases import CancelPurchase, CreatePurchase, ReceivePurchase
from app.domain.inventory.errors import BranchNotFoundError, ProductNotFoundError
from app.domain.purchasing import rules
from app.domain.catalog.errors import SupplierNotFoundError
from app.domain.purchasing.errors import (
    InvalidPurchaseError,
    PurchaseNotFoundError,
    PurchaseNotReceivableError,
)


class World:
    def __init__(self, purchase=None, products=(1, 2), branches=(1,), suppliers=(1,), fail_on=None):
        self.purchase = purchase
        self.products, self.branches, self.suppliers = set(products), set(branches), set(suppliers)
        self.fail_on = fail_on
        self.created = None
        self.received, self.costs = [], {}
        self.status = None
        self.commits = self.rollbacks = 0

    async def create(self, command, total):
        self.created = (command, total)
        return 7

    async def get(self, tenant_id, purchase_id):
        return self.purchase

    async def mark_received(self, purchase_id):
        self.status = "received"

    async def mark_cancelled(self, purchase_id):
        self.status = "cancelled"

    async def receive(self, tenant_id, user_id, product_id, branch_id, quantity, unit_cost, reference, notes):
        if product_id == self.fail_on:
            raise RuntimeError("boom")
        self.received.append((product_id, branch_id, quantity, reference))

    async def set_product_cost(self, tenant_id, product_id, cost):
        self.costs[product_id] = cost

    async def missing_products(self, tenant_id, ids):
        return set(ids) - self.products

    async def branch_exists(self, tenant_id, branch_id):
        return branch_id in self.branches

    async def supplier_exists(self, tenant_id, supplier_id):
        return supplier_id in self.suppliers

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def create_cmd(items=None, **kw):
    items = items if items is not None else [PurchaseItemInput(1, 2, Decimal("5.50"))]
    base = dict(tenant_id=1, user_id=2, supplier_id=1, branch_id=1, items=tuple(items))
    return CreatePurchaseCommand(**{**base, **kw})


def draft(items=None, status="draft"):
    items = items or (PurchaseItemInput(1, 2, Decimal("4")), PurchaseItemInput(2, 1, Decimal("9")))
    return PurchaseSnapshot(7, status, 1, "F-001", tuple(items))


ACTION = PurchaseActionCommand(purchase_id=7, tenant_id=1, user_id=2)


def test_total_rule():
    items = [PurchaseItemInput(1, 2, Decimal("5.50")), PurchaseItemInput(2, 3, Decimal("1"))]
    assert rules.purchase_total(items) == Decimal("14.00")


async def test_create_purchase_computes_total_and_commits():
    w = World()
    assert await CreatePurchase(w, w, w).execute(create_cmd()) == 7
    assert w.created[1] == Decimal("11.00") and w.commits == 1


async def test_create_purchase_rejects_foreign_or_empty_resources():
    w = World()
    uc = CreatePurchase(w, w, w)
    with pytest.raises(InvalidPurchaseError):
        await uc.execute(create_cmd(items=[]))
    with pytest.raises(SupplierNotFoundError):
        await uc.execute(create_cmd(supplier_id=9))
    with pytest.raises(BranchNotFoundError):
        await uc.execute(create_cmd(branch_id=9))
    with pytest.raises(ProductNotFoundError):
        await uc.execute(create_cmd(items=[PurchaseItemInput(99, 1, Decimal("1"))]))
    assert w.created is None and w.rollbacks == 4


async def test_receive_purchase_adds_stock_updates_cost_and_marks_received():
    w = World(purchase=draft())
    await ReceivePurchase(w, w, w).execute(ACTION)
    assert w.received == [(1, 1, 2, "Compra #7 F-001"), (2, 1, 1, "Compra #7 F-001")]
    assert w.costs == {1: Decimal("4"), 2: Decimal("9")}
    assert w.status == "received" and (w.commits, w.rollbacks) == (1, 0)


async def test_receive_is_all_or_nothing():
    w = World(purchase=draft(), fail_on=2)
    with pytest.raises(RuntimeError):
        await ReceivePurchase(w, w, w).execute(ACTION)
    assert w.status is None and w.commits == 0 and w.rollbacks == 1


async def test_receive_requires_existing_draft():
    for purchase in (None, draft(status="received"), draft(status="cancelled")):
        w = World(purchase=purchase)
        with pytest.raises(PurchaseNotReceivableError):
            await ReceivePurchase(w, w, w).execute(ACTION)
        assert not w.received


async def test_cancel_only_drafts():
    w = World(purchase=draft())
    await CancelPurchase(w, w).execute(ACTION)
    assert w.status == "cancelled"

    w = World(purchase=draft(status="received"))
    with pytest.raises(InvalidPurchaseError):
        await CancelPurchase(w, w).execute(ACTION)

    w = World()
    with pytest.raises(PurchaseNotFoundError):
        await CancelPurchase(w, w).execute(ACTION)
