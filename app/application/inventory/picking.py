"""Lista de picking: ítems de una venta ordenados por su ubicación en bodega."""

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.inventory import rules


@dataclass(frozen=True)
class PickingLine:
    item_id: int
    product_id: int
    product_name: str
    sku: str
    quantity: int
    aisle: str | None
    shelf: str | None
    bin: str | None


class PickingReader(Protocol):
    async def lines_for_sale(self, tenant_id: int, sale_id: int) -> list[PickingLine] | None:
        """None si la venta no existe para el tenant."""
        ...


class GetPickingList:
    def __init__(self, reader: PickingReader):
        self.reader = reader

    async def execute(self, tenant_id: int, sale_id: int) -> list[dict[str, Any]]:
        lines = await self.reader.lines_for_sale(tenant_id, sale_id) or []
        ordered = sorted(
            lines,
            key=lambda l: (
                rules.natural_sort_key(l.aisle), rules.natural_sort_key(l.shelf), rules.natural_sort_key(l.bin)
            ),
        )
        return [
            {
                "item_id": l.item_id,
                "product_id": l.product_id,
                "product_name": l.product_name,
                "sku": l.sku,
                "quantity": l.quantity,
                "aisle": l.aisle,
                "shelf": l.shelf,
                "bin": l.bin,
                "location_str": (
                    f"{l.aisle or ''}-{l.shelf or ''}-{l.bin or ''}".strip("-")
                    if any((l.aisle, l.shelf, l.bin)) else "SIN UBICACIÓN"
                ),
            }
            for l in ordered
        ]
