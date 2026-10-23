"""Reglas de negocio puras de ventas (sin I/O)."""

from decimal import Decimal

from app.domain.sales.errors import (
    InvalidCashAmountError,
    InvalidLoyaltyAdjustmentError,
    InvalidLoyaltyConfigError,
    InvalidPaymentError,
    PaymentExceedsBalanceError,
)

CREDIT_PAYMENT_METHOD = "credit"
CASH_PAYMENT_METHOD = "cash"
ANNULLED_STATUS = "annulled"


def line_subtotal(quantity: int, unit_price: Decimal) -> Decimal:
    return Decimal(str(quantity)) * Decimal(str(unit_price))


def redemption_discount(points: int, amount_per_point: Decimal, order_total: Decimal) -> Decimal:
    """Descuento por puntos redimidos; nunca supera el total de la orden."""
    return min(Decimal(str(points)) * amount_per_point, order_total)


def earned_points(total: Decimal, points_per_amount: Decimal) -> int:
    """Puntos ganados: 1 punto por cada `points_per_amount` gastado."""
    if points_per_amount <= 0:
        return 0
    return int(total / points_per_amount)


def validate_cash_amount(amount: Decimal) -> None:
    if amount < 0:
        raise InvalidCashAmountError()


def expected_cash_balance(opening: Decimal, cash_sales: Decimal, expenses: Decimal) -> Decimal:
    """Efectivo esperado en caja: apertura + ventas en efectivo - gastos pagados de caja."""
    return opening + cash_sales - expenses


def apply_credit_payment(remaining: Decimal, amount: Decimal) -> Decimal:
    """Devuelve el nuevo saldo tras un abono; rechaza montos no positivos o mayores al saldo."""
    if amount <= 0:
        raise InvalidPaymentError()
    if amount > remaining:
        raise PaymentExceedsBalanceError(amount, remaining)
    return remaining - amount


def validate_loyalty_config(changes: dict) -> None:
    for key in ("points_per_amount", "amount_per_point"):
        if key in changes and changes[key] is not None and changes[key] <= 0:
            raise InvalidLoyaltyConfigError(f"{key} debe ser mayor a 0")
    minimum = changes.get("min_redemption_points")
    if minimum is not None and minimum < 0:
        raise InvalidLoyaltyConfigError("min_redemption_points no puede ser negativo")


def validate_loyalty_adjustment(current_points: int, delta: int) -> None:
    if delta == 0:
        raise InvalidLoyaltyAdjustmentError("El ajuste de puntos no puede ser 0")
    if current_points + delta < 0:
        raise InvalidLoyaltyAdjustmentError("El ajuste dejaría al cliente con puntos negativos")
