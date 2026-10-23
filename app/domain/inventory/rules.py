"""Reglas puras de inventario."""

import re

from app.domain.inventory.errors import InvalidAdjustmentError

ADJUSTMENT_IN = "IN"
ADJUSTMENT_OUT = "OUT"
TRANSFER_PENDING = "pending"
TRANSFER_COMPLETED = "completed"
TRANSFER_CANCELLED = "cancelled"


def signed_adjustment(adjustment_type: str, quantity: float) -> int:
    """Convierte un ajuste IN/OUT en un delta entero con signo."""
    if adjustment_type not in (ADJUSTMENT_IN, ADJUSTMENT_OUT):
        raise InvalidAdjustmentError("Tipo de ajuste inválido. Use IN o OUT")
    if quantity <= 0 or quantity != int(quantity):
        raise InvalidAdjustmentError("La cantidad debe ser un entero mayor a 0")
    amount = int(quantity)
    return amount if adjustment_type == ADJUSTMENT_IN else -amount


# --- alertas de stock ---------------------------------------------------------
OUT_OF_STOCK = "out_of_stock"
LOW_STOCK = "low_stock"


def stock_alert_type(stock: int, min_stock: int) -> str | None:
    """Tipo de alerta que corresponde al nivel de stock (None si está sano)."""
    if stock <= 0:
        return OUT_OF_STOCK
    if stock <= min_stock:
        return LOW_STOCK
    return None


def alert_threshold(alert_type: str, min_stock: int) -> int:
    return 0 if alert_type == OUT_OF_STOCK else min_stock


def alert_message(alert_type: str, name: str, stock: int, min_stock: int) -> str:
    if alert_type == OUT_OF_STOCK:
        return f"Producto '{name}' sin stock"
    return f"Stock bajo para '{name}': {stock} unidades (mínimo: {min_stock})"


def alert_is_resolved(alert_type: str, stock: int, min_stock: int) -> bool:
    """Una alerta activa deja de aplicar cuando el stock se recupera por encima de su umbral."""
    if alert_type == OUT_OF_STOCK:
        return stock > 0
    if alert_type == LOW_STOCK:
        return stock > min_stock
    return False


# --- picking ------------------------------------------------------------------
_DIGITS = re.compile(r"(\d+)")


def natural_sort_key(text: str | None) -> list[tuple[int, int, str]]:
    """Orden natural (A1, A2, A10); comparable aunque se mezclen números y texto; vacíos al final."""
    if not text:
        return [(2, 0, "")]
    return [
        (0, int(part), "") if part.isdigit() else (1, 0, part.lower())
        for part in _DIGITS.split(text)
        if part != ""
    ]
