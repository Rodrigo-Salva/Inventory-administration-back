"""Reglas puras del catálogo: normalización de filas de importación."""

from decimal import Decimal, InvalidOperation
from typing import Mapping

from app.domain.catalog.errors import ProductRowError

MAX_IMPORT_ROWS = 5000


def parse_csv_row(row: Mapping[str, str | None]) -> dict:
    """Convierte una fila CSV (español o inglés) en atributos de producto."""
    sku = (row.get("sku") or "").strip()
    if not sku:
        raise ProductRowError("Fila omitida: Falta SKU")
    name = (row.get("nombre") or row.get("name") or "").strip()
    if not name:
        raise ProductRowError(f"SKU {sku}: Falta nombre")
    try:
        price = Decimal((row.get("precio") or row.get("price") or "0").replace(",", "."))
        cost_raw = row.get("costo") or row.get("cost")
        cost = Decimal(cost_raw.replace(",", ".")) if cost_raw else None
        stock = int(row.get("stock") or "0")
        min_stock = int(row.get("min_stock") or 10)
    except (InvalidOperation, ValueError):
        raise ProductRowError(f"SKU {sku}: valores numéricos inválidos")
    if price <= 0 or (cost is not None and cost < 0) or stock < 0 or min_stock < 0:
        raise ProductRowError(f"SKU {sku}: precio, costo o stock fuera de rango")
    return {
        "name": name,
        "sku": sku,
        "price": price,
        "cost": cost,
        "stock": stock,
        "barcode": row.get("codigo_barras") or row.get("barcode") or None,
        "description": row.get("descripcion") or row.get("description"),
        "min_stock": min_stock,
    }
