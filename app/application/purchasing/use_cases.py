from app.application.purchasing.dto import CreatePurchaseCommand, PurchaseActionCommand
from app.application.purchasing.ports import PurchaseStore, StockReceiptPort
from app.application.shared.ports import TenantResources, UnitOfWork
from app.domain.inventory.errors import BranchNotFoundError, ProductNotFoundError
from app.domain.purchasing import rules
from app.domain.catalog.errors import SupplierNotFoundError
from app.domain.purchasing.errors import (
    InvalidPurchaseError,
    PurchaseNotFoundError,
    PurchaseNotReceivableError,
)


class CreatePurchase:
    """Crea una compra en borrador validando que todo pertenezca al tenant."""

    def __init__(self, purchases: PurchaseStore, resources: TenantResources, uow: UnitOfWork):
        self.purchases = purchases
        self.resources = resources
        self.uow = uow

    async def execute(self, cmd: CreatePurchaseCommand) -> int:
        try:
            if not cmd.items:
                raise InvalidPurchaseError("La compra debe tener al menos un ítem")
            if not await self.resources.supplier_exists(cmd.tenant_id, cmd.supplier_id):
                raise SupplierNotFoundError()
            if not await self.resources.branch_exists(cmd.tenant_id, cmd.branch_id):
                raise BranchNotFoundError()
            missing = await self.resources.missing_products(
                cmd.tenant_id, {i.product_id for i in cmd.items}
            )
            if missing:
                raise ProductNotFoundError(sorted(missing)[0])
            purchase_id = await self.purchases.create(cmd, rules.purchase_total(cmd.items))
            await self.uow.commit()
            return purchase_id
        except Exception:
            await self.uow.rollback()
            raise


class ReceivePurchase:
    """Recibe una compra: ingresa stock en la sucursal y actualiza costos, de forma atómica."""

    def __init__(self, purchases: PurchaseStore, stock: StockReceiptPort, uow: UnitOfWork):
        self.purchases = purchases
        self.stock = stock
        self.uow = uow

    async def execute(self, cmd: PurchaseActionCommand) -> int:
        try:
            purchase = await self.purchases.get(cmd.tenant_id, cmd.purchase_id)
            if not purchase or purchase.status != rules.PURCHASE_DRAFT:
                raise PurchaseNotReceivableError()
            for item in purchase.items:
                await self.stock.receive(
                    cmd.tenant_id, cmd.user_id, item.product_id, purchase.branch_id,
                    item.quantity, item.unit_cost,
                    f"Compra #{purchase.id} {purchase.reference_number or ''}",
                    "Recepción de compra automatizada",
                )
                await self.stock.set_product_cost(cmd.tenant_id, item.product_id, item.unit_cost)
            await self.purchases.mark_received(purchase.id)
            await self.uow.commit()
            return purchase.id
        except Exception:
            await self.uow.rollback()
            raise


class CancelPurchase:
    def __init__(self, purchases: PurchaseStore, uow: UnitOfWork):
        self.purchases = purchases
        self.uow = uow

    async def execute(self, cmd: PurchaseActionCommand) -> int:
        try:
            purchase = await self.purchases.get(cmd.tenant_id, cmd.purchase_id)
            if not purchase:
                raise PurchaseNotFoundError()
            if purchase.status != rules.PURCHASE_DRAFT:
                raise InvalidPurchaseError("Solo se pueden cancelar compras en estado Borrador")
            await self.purchases.mark_cancelled(purchase.id)
            await self.uow.commit()
            return purchase.id
        except Exception:
            await self.uow.rollback()
            raise
