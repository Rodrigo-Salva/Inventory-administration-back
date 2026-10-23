from decimal import Decimal
from typing import Iterable, Protocol

PURCHASE_DRAFT = "draft"
PURCHASE_RECEIVED = "received"
PURCHASE_CANCELLED = "cancelled"


class _Line(Protocol):
    quantity: int
    unit_cost: Decimal


def purchase_total(lines: Iterable[_Line]) -> Decimal:
    return sum((Decimal(line.quantity) * line.unit_cost for line in lines), Decimal(0))
