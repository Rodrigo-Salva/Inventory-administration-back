import pytest

from app.application.inventory.dto import (
    CreateAdjustmentCommand,
    CreateTransferCommand,
    StockProduct,
    TransferActionCommand,
    TransferItem,
    TransferSnapshot,
)
from app.application.inventory.use_cases import (
    CancelStockTransfer,
    CompleteStockTransfer,
    CreateAdjustment,
    CreateStockTransfer,
)
from app.domain.inventory import rules
from app.domain.inventory.errors import (
    BranchNotFoundError,
    InsufficientBranchStockError,
    InsufficientStockError,
    InvalidAdjustmentError,
    InvalidTransferError,
    ProductNotFoundError,
    TransferNotFoundError,
)


class World:
    """Doble en memoria de AdjustmentStore, TransferStore, BranchStockPort, TenantResources y UoW."""

    def __init__(self, products=None, branch_stock=None, branches=(1, 2), transfer=None):
        self.products = products or {}  # id -> [name, stock]
        self.branch_stock = branch_stock or {}  # (product, branch) -> qty
        self.branches = set(branches)
        self.transfer = transfer
        self.recorded = None
        self.moved = []
        self.status = None
        self.commits = self.rollbacks = 0

    # AdjustmentStore
    async def lock_product(self, tenant_id, product_id, branch_id=None):
        self.locked_branch = branch_id
        p = self.products.get(product_id)
        return StockProduct(product_id, p[0], p[1]) if p else None

    async def record(self, command, delta, stock_before, branch_id=None):
        self.recorded = (delta, stock_before)
        self.recorded_branch = branch_id
        return 5

    # TransferStore
    async def create(self, command):
        return 10

    async def get(self, tenant_id, transfer_id):
        return self.transfer

    async def mark_completed(self, transfer_id):
        self.status = "completed"

    async def mark_cancelled(self, transfer_id):
        self.status = "cancelled"

    # BranchStockPort
    async def available(self, tenant_id, product_id, branch_id):
        return self.branch_stock.get((product_id, branch_id), 0)

    async def move(self, tenant_id, user_id, transfer_id, from_branch_id, to_branch_id, item):
        self.branch_stock[(item.product_id, from_branch_id)] -= item.quantity
        key = (item.product_id, to_branch_id)
        self.branch_stock[key] = self.branch_stock.get(key, 0) + item.quantity
        self.moved.append((item.product_id, from_branch_id, to_branch_id, item.quantity))

    # TenantResources
    async def missing_products(self, tenant_id, ids):
        return {i for i in ids if i not in self.products}

    async def branch_exists(self, tenant_id, branch_id):
        return branch_id in self.branches

    async def supplier_exists(self, tenant_id, supplier_id):
        return True

    # UnitOfWork
    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def adjust(**kw):
    base = dict(tenant_id=1, user_id=2, product_id=1, adjustment_type="OUT", quantity=3, reason="DAMAGE")
    return CreateAdjustmentCommand(**{**base, **kw})


def transfer_cmd(items, **kw):
    base = dict(tenant_id=1, user_id=2, from_branch_id=1, to_branch_id=2, items=tuple(items))
    return CreateTransferCommand(**{**base, **kw})


def test_signed_adjustment_rules():
    assert rules.signed_adjustment("IN", 4) == 4
    assert rules.signed_adjustment("OUT", 4.0) == -4
    for bad in (("IN", 0), ("IN", -1), ("OUT", 1.5), ("XX", 1)):
        with pytest.raises(InvalidAdjustmentError):
            rules.signed_adjustment(*bad)


async def test_adjustment_out_reduces_stock():
    w = World(products={1: ["Cafe", 10]})
    assert await CreateAdjustment(w, w).execute(adjust()) == 5
    assert w.recorded == (-3, 10) and (w.commits, w.rollbacks) == (1, 0)


async def test_adjustment_cannot_make_stock_negative_or_use_foreign_product():
    w = World(products={1: ["Cafe", 2]})
    with pytest.raises(InsufficientStockError):
        await CreateAdjustment(w, w).execute(adjust(quantity=3))
    assert w.rollbacks == 1 and w.recorded is None
    with pytest.raises(ProductNotFoundError):
        await CreateAdjustment(w, w).execute(adjust(product_id=99))


async def test_pending_transfer_does_not_move_stock():
    w = World(products={1: ["Cafe", 10]}, branch_stock={(1, 1): 5})
    await CreateStockTransfer(w, w, w, w).execute(transfer_cmd([TransferItem(1, 2)]))
    assert not w.moved and w.status is None and w.commits == 1


async def test_transfer_completed_on_create_moves_stock():
    w = World(products={1: ["Cafe", 10]}, branch_stock={(1, 1): 5})
    await CreateStockTransfer(w, w, w, w).execute(transfer_cmd([TransferItem(1, 2)], complete_now=True))
    assert w.moved == [(1, 1, 2, 2)] and w.status == "completed"
    assert w.branch_stock == {(1, 1): 3, (1, 2): 2}


async def test_transfer_validations():
    w = World(products={1: ["Cafe", 10]}, branch_stock={(1, 1): 5})
    uc = CreateStockTransfer(w, w, w, w)
    with pytest.raises(InvalidTransferError):
        await uc.execute(transfer_cmd([TransferItem(1, 1)], to_branch_id=1))
    with pytest.raises(InvalidTransferError):
        await uc.execute(transfer_cmd([]))
    with pytest.raises(BranchNotFoundError):
        await uc.execute(transfer_cmd([TransferItem(1, 1)], to_branch_id=77))
    with pytest.raises(ProductNotFoundError):
        await uc.execute(transfer_cmd([TransferItem(55, 1)]))
    with pytest.raises(InsufficientBranchStockError):
        await uc.execute(transfer_cmd([TransferItem(1, 9)], complete_now=True))
    assert not w.moved


async def test_complete_and_cancel_only_when_pending():
    pending = TransferSnapshot(10, 3, "pending", 1, 2, (TransferItem(1, 2),))
    w = World(products={1: ["Cafe", 10]}, branch_stock={(1, 1): 5}, transfer=pending)
    await CompleteStockTransfer(w, w, w).execute(TransferActionCommand(10, 1))
    assert w.status == "completed" and w.moved

    w = World(transfer=pending)
    await CancelStockTransfer(w, w).execute(TransferActionCommand(10, 1))
    assert w.status == "cancelled"

    done = TransferSnapshot(10, 3, "completed", 1, 2, ())
    w = World(transfer=done)
    with pytest.raises(InvalidTransferError):
        await CompleteStockTransfer(w, w, w).execute(TransferActionCommand(10, 1))
    with pytest.raises(InvalidTransferError):
        await CancelStockTransfer(w, w).execute(TransferActionCommand(10, 1))

    w = World()
    with pytest.raises(TransferNotFoundError):
        await CancelStockTransfer(w, w).execute(TransferActionCommand(10, 1))


class FakeBranches:
    async def resolve(self, tenant_id, user_id, requested_branch_id=None):
        return requested_branch_id or 7


async def test_adjustment_operates_on_the_resolved_branch():
    w = World(products={1: ["Cafe", 10]})
    await CreateAdjustment(w, w, FakeBranches()).execute(adjust())
    assert w.locked_branch == 7 and w.recorded_branch == 7
    await CreateAdjustment(w, w, FakeBranches()).execute(adjust(branch_id=2))
    assert w.locked_branch == 2 and w.recorded_branch == 2
