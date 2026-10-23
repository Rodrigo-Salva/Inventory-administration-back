from decimal import Decimal

from app.application.sales.dto import AnnulSaleCommand, CreateSaleCommand
from app.application.sales.ports import CreditPort, InventoryPort, LoyaltyPort, SaleStore
from app.application.shared.ports import UnitOfWork
from app.domain.inventory.errors import (
    BatchNotFoundError,
    InsufficientStockError,
    ProductNotFoundError,
)
from app.domain.sales import rules
from app.domain.sales.errors import (
    CreditCustomerRequiredError,
    InsufficientCreditError,
    InsufficientLoyaltyPointsError,
    LoyaltyMinimumNotMetError,
    SaleAlreadyAnnulledError,
    SaleNotFoundError,
)


class CreateSale:
    """Registra una venta: stock, lotes, movimientos, lealtad y crédito en una transacción."""

    def __init__(
        self,
        sales: SaleStore,
        inventory: InventoryPort,
        loyalty: LoyaltyPort,
        credit: CreditPort,
        uow: UnitOfWork,
        cash_sessions=None,
        branches=None,
    ):
        self.sales = sales
        self.inventory = inventory
        self.loyalty = loyalty
        self.credit = credit
        self.uow = uow
        self.cash_sessions = cash_sessions  # CashSessionStore opcional
        self.branches = branches  # BranchResolver: sucursal que despacha la venta

    async def execute(self, command: CreateSaleCommand) -> int:
        try:
            sale_id = await self.register(command)
            await self.uow.commit()
            return sale_id
        except Exception:
            await self.uow.rollback()
            raise

    async def register(self, cmd: CreateSaleCommand) -> int:
        """Registra la venta SIN cerrar la transacción (para componerla con otros pasos)."""
        session = await self.cash_sessions.get_active(cmd.tenant_id, cmd.user_id) if self.cash_sessions else None
        branch_id = (
            await self.branches.resolve(cmd.tenant_id, cmd.user_id, cmd.branch_id) if self.branches else cmd.branch_id
        )
        sale_id = await self.sales.create(
            cmd.tenant_id, cmd.user_id, cmd.payment_method, cmd.notes, session.id if session else None, branch_id
        )

        total = Decimal(0)
        for line in cmd.lines:
            product = await self.inventory.get_product(cmd.tenant_id, line.product_id, branch_id)
            if not product:
                raise ProductNotFoundError(line.product_id)
            if product.stock < line.quantity:
                raise InsufficientStockError(product.name, line.quantity, product.stock)

            subtotal = rules.line_subtotal(line.quantity, line.unit_price)
            total += subtotal
            await self.sales.add_item(sale_id, line, subtotal)

            if line.batch_id:
                batch = await self.inventory.get_batch(cmd.tenant_id, line.batch_id)
                if not batch:
                    raise BatchNotFoundError(line.batch_id)
                if batch.quantity < line.quantity:
                    raise InsufficientStockError(
                        f"{product.name} (Lote: {batch.number})", line.quantity, batch.quantity
                    )

            await self.inventory.register_sale_exit(
                cmd.tenant_id, cmd.user_id, sale_id, product.id, line.batch_id, line.quantity, branch_id
            )

        program = await self.loyalty.get_active_program(cmd.tenant_id)

        discount = Decimal(0)
        redeemed = 0
        if cmd.redeemed_points > 0 and cmd.customer_id:
            points = await self.loyalty.get_points(cmd.tenant_id, cmd.customer_id)
            if points is None or points < cmd.redeemed_points:
                raise InsufficientLoyaltyPointsError()
            if not program or cmd.redeemed_points < program.min_redemption_points:
                raise LoyaltyMinimumNotMetError(program.min_redemption_points if program else 0)
            discount = rules.redemption_discount(
                cmd.redeemed_points, program.amount_per_point, total
            )
            total -= discount
            redeemed = cmd.redeemed_points
            await self.loyalty.redeem(cmd.tenant_id, cmd.customer_id, sale_id, redeemed)

        await self.sales.finalize(sale_id, total, cmd.customer_id, redeemed, discount)

        if cmd.payment_method == rules.CREDIT_PAYMENT_METHOD:
            if not cmd.customer_id:
                raise CreditCustomerRequiredError()
            if not await self.credit.has_available_credit(cmd.tenant_id, cmd.customer_id, total):
                raise InsufficientCreditError()
            await self.credit.open_credit(cmd.tenant_id, cmd.customer_id, sale_id, total)

        if cmd.customer_id and program:
            earned = rules.earned_points(total, program.points_per_amount)
            if earned > 0:
                await self.loyalty.earn(cmd.tenant_id, cmd.customer_id, sale_id, earned)

        return sale_id


class AnnulSale:
    """Anula una venta y revierte stock, crédito y puntos de lealtad."""

    def __init__(
        self,
        sales: SaleStore,
        inventory: InventoryPort,
        loyalty: LoyaltyPort,
        credit: CreditPort,
        uow: UnitOfWork,
    ):
        self.sales = sales
        self.inventory = inventory
        self.loyalty = loyalty
        self.credit = credit
        self.uow = uow

    async def execute(self, command: AnnulSaleCommand) -> int:
        try:
            await self._annul(command)
            await self.uow.commit()
            return command.sale_id
        except Exception:
            await self.uow.rollback()
            raise

    async def _annul(self, cmd: AnnulSaleCommand) -> None:
        sale = await self.sales.get_for_annulment(cmd.sale_id, cmd.tenant_id)
        if not sale:
            raise SaleNotFoundError()
        if sale.status == rules.ANNULLED_STATUS:
            raise SaleAlreadyAnnulledError()

        for item in sale.items:
            await self.inventory.register_annulment_entry(
                cmd.tenant_id, cmd.user_id, sale.id, item.product_id, item.batch_id, item.quantity,
                sale.branch_id,
            )
        await self.sales.mark_annulled(sale.id)
        await self.credit.annul_for_sale(cmd.tenant_id, sale.id)
        await self.loyalty.reverse_for_sale(cmd.tenant_id, sale.id)
