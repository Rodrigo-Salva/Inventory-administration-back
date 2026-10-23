import pytest

from app.application.inventory.dto import (
    AddStockCommand,
    AdjustStockToCommand,
    AuditItemSnapshot,
    AuditSnapshot,
    CompleteAuditCommand,
    CountAuditItemCommand,
    RemoveStockCommand,
    StartAuditCommand,
    StockPosition,
)
from app.application.inventory.stock_use_cases import (
    AddStock,
    AdjustStockTo,
    CompleteAudit,
    CountAuditItem,
    RemoveStock,
    StartAudit,
)
from app.domain.inventory.errors import (
    BranchNotFoundError,
    InsufficientStockError,
    InvalidAuditError,
    InvalidStockOperationError,
    ProductNotFoundError,
)


class World:
    """Doble en memoria de BranchLedger, AuditStore, TenantResources y UnitOfWork."""

    def __init__(self, stock=None, products=(1, 2), branches=(1,), audit=None):
        self.stock = stock or {}  # (product, branch) -> qty
        self.products, self.branches = set(products), set(branches)
        self.audit = audit
        self.posts, self.upserts, self.adjusted = [], [], []
        self.completed = False
        self.commits = self.rollbacks = 0

    # BranchLedger
    async def open_position(self, tenant_id, product_id, branch_id, aisle=None, shelf=None, bin=None):
        if product_id not in self.products:
            return None
        return StockPosition(product_id, f"P{product_id}", self.stock.get((product_id, branch_id), 0))

    async def current_stock(self, tenant_id, product_id, branch_id):
        return self.stock.get((product_id, branch_id), 0)

    async def post(self, tenant_id, user_id, product_id, branch_id, delta, movement_type, unit_cost=None, reference=None, notes=None):
        key = (product_id, branch_id)
        self.stock[key] = self.stock.get(key, 0) + delta
        self.posts.append((product_id, delta, movement_type, notes))
        return 50

    # AuditStore
    async def create(self, command):
        return 8

    async def get(self, tenant_id, audit_id):
        return self.audit

    async def upsert_item(self, audit_id, product_id, expected, counted, notes):
        self.upserts.append((product_id, expected, counted))
        return 3

    async def mark_item_adjusted(self, item_id):
        self.adjusted.append(item_id)

    async def complete(self, audit_id):
        self.completed = True

    # TenantResources
    async def missing_products(self, tenant_id, ids):
        return set(ids) - self.products

    async def branch_exists(self, tenant_id, branch_id):
        return branch_id in self.branches

    async def supplier_exists(self, tenant_id, supplier_id):
        return True

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def add(q=5, **kw):
    return AddStockCommand(tenant_id=1, user_id=2, product_id=1, branch_id=1, quantity=q, **kw)


async def test_add_stock():
    w = World(stock={(1, 1): 2})
    assert await AddStock(w, w, w).execute(add(5)) == 50
    assert w.stock[(1, 1)] == 7 and w.posts[0][2] == "entry" and w.commits == 1


async def test_add_stock_validations():
    w = World()
    uc = AddStock(w, w, w)
    with pytest.raises(InvalidStockOperationError):
        await uc.execute(add(0))
    with pytest.raises(BranchNotFoundError):
        await uc.execute(AddStockCommand(1, 2, 1, 9, 1))
    with pytest.raises(ProductNotFoundError):
        await uc.execute(AddStockCommand(1, 2, 99, 1, 1))
    assert not w.posts and w.rollbacks == 3


async def test_remove_stock_checks_branch_stock():
    w = World(stock={(1, 1): 4})
    uc = RemoveStock(w, w, w)
    await uc.execute(RemoveStockCommand(1, 2, 1, 1, 3))
    assert w.stock[(1, 1)] == 1 and w.posts[0][1:3] == (-3, "exit")
    with pytest.raises(InsufficientStockError) as err:
        await uc.execute(RemoveStockCommand(1, 2, 1, 1, 3))
    assert "Disponible: 1" in str(err.value)


async def test_adjust_stock_to_exact_value():
    w = World(stock={(1, 1): 10})
    uc = AdjustStockTo(w, w, w)
    await uc.execute(AdjustStockToCommand(1, 2, 1, 1, 6, "merma"))
    assert w.stock[(1, 1)] == 6
    assert w.posts[0] == (1, -4, "adjustment", "Ajuste de inventario: merma")
    with pytest.raises(InvalidStockOperationError):
        await uc.execute(AdjustStockToCommand(1, 2, 1, 1, 6))  # igual al actual
    with pytest.raises(InvalidStockOperationError):
        await uc.execute(AdjustStockToCommand(1, 2, 1, 1, -1))


async def test_start_and_count_audit():
    w = World(stock={(1, 1): 7}, audit=AuditSnapshot(8, 1, "in_progress", ()))
    assert await StartAudit(w, w, w).execute(StartAuditCommand(1, 2, 1)) == 8
    await CountAuditItem(w, w, w, w).execute(CountAuditItemCommand(1, 8, 1, 5))
    assert w.upserts == [(1, 7, 5)]

    with pytest.raises(BranchNotFoundError):
        await StartAudit(w, w, w).execute(StartAuditCommand(1, 2, 9))
    with pytest.raises(ProductNotFoundError):
        await CountAuditItem(w, w, w, w).execute(CountAuditItemCommand(1, 8, 99, 1))
    w.audit = AuditSnapshot(8, 1, "completed", ())
    with pytest.raises(InvalidAuditError):
        await CountAuditItem(w, w, w, w).execute(CountAuditItemCommand(1, 8, 1, 1))


async def test_complete_audit_adjusts_differences_atomically():
    items = (
        AuditItemSnapshot(1, 1, counted_stock=5, difference=-3, is_adjusted=False),
        AuditItemSnapshot(2, 2, counted_stock=9, difference=0, is_adjusted=False),   # sin diferencia
        AuditItemSnapshot(3, 2, counted_stock=1, difference=1, is_adjusted=True),     # ya ajustado
    )
    w = World(stock={(1, 1): 8, (2, 1): 9}, audit=AuditSnapshot(8, 1, "in_progress", items))
    await CompleteAudit(w, w, w, w).execute(CompleteAuditCommand(1, 2, 8))
    assert w.stock[(1, 1)] == 5 and len(w.posts) == 1
    assert w.adjusted == [1] and w.completed and w.commits == 1


async def test_complete_audit_skips_items_that_already_match_and_rolls_back_on_error():
    item = AuditItemSnapshot(1, 1, counted_stock=5, difference=-3, is_adjusted=False)
    w = World(stock={(1, 1): 5}, audit=AuditSnapshot(8, 1, "in_progress", (item,)))
    await CompleteAudit(w, w, w, w).execute(CompleteAuditCommand(1, 2, 8))
    assert not w.posts and w.adjusted == [1] and w.completed

    bad = AuditItemSnapshot(1, 99, counted_stock=5, difference=1, is_adjusted=False)
    w = World(audit=AuditSnapshot(8, 1, "in_progress", (bad,)))
    with pytest.raises(ProductNotFoundError):
        await CompleteAudit(w, w, w, w).execute(CompleteAuditCommand(1, 2, 8))
    assert not w.completed and w.commits == 0 and w.rollbacks == 1
