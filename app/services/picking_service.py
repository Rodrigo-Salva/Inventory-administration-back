import re
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from ..models.sale import Sale, SaleItem
from ..models.product_branch import ProductBranch
from ..models.product import Product
from ..core.exceptions import ProductNotFoundException

class PickingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _natural_sort_key(self, text: Optional[str]) -> List[Any]:
        """
        Genera una clave para ordenamiento natural (A1, A2, A10 en lugar de A1, A10, A2).
        """
        if not text:
            return [float('inf')] # Mandar al final los que no tienen ubicación
        
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', text)
        ]

    async def get_picking_list(self, sale_id: int, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene los items de una venta con sus ubicaciones en bodega,
        ordenados de forma óptima para el recolector (picking).
        """
        # 1. Obtener la venta y sus items
        # Nota: Normalmente una venta sale de una sucursal específica. 
        # Si el modelo Sale no tiene branch_id directamente, lo inferimos del usuario o la sucursal del primer producto.
        # En este sistema, las ventas suelen estar asociadas a una caja o sucursal.
        
        from ..models.sale import Sale, SaleItem
        from sqlalchemy.orm import joinedload
        
        query = select(Sale).options(
            joinedload(Sale.items).joinedload(SaleItem.product),
            joinedload(Sale.user)
        ).where(
            and_(Sale.id == sale_id, Sale.tenant_id == tenant_id)
        )
        result = await self.db.execute(query)
        sale = result.unique().scalar_one_or_none()
        
        if not sale:
            return []

        # Determinar la sucursal de donde se descontó (usualmente la del usuario)
        branch_id = sale.user.branch_id if sale.user else None
        
        if not branch_id:
            # Fallback: intentar obtener la primera sucursal donde hay movimiento para esta venta
            from ..models.inventory_movement import InventoryMovement
            mov_query = select(InventoryMovement.branch_id).where(
                InventoryMovement.reference == f"VENTA #{sale_id}",
                InventoryMovement.tenant_id == tenant_id
            ).limit(1)
            mov_res = await self.db.execute(mov_query)
            branch_id = mov_res.scalar_one_or_none()

        picking_items = []

        for item in sale.items:
            # 2. Buscar ubicación en product_branches
            pb_query = select(ProductBranch).where(
                and_(
                    ProductBranch.product_id == item.product_id,
                    ProductBranch.branch_id == branch_id
                )
            )
            pb_res = await self.db.execute(pb_query)
            pb = pb_res.scalar_one_or_none()

            picking_items.append({
                "item_id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "sku": item.product.sku,
                "quantity": item.quantity,
                "aisle": pb.aisle if pb else None,
                "shelf": pb.shelf if pb else None,
                "bin": pb.bin if pb else None,
                "location_str": f"{pb.aisle or ''}-{pb.shelf or ''}-{pb.bin or ''}".strip("-") if pb else "SIN UBICACIÓN"
            })

        # 3. Ordenar por Pasillo, Estante, Gaveta (Ordenamiento Natural)
        picking_items.sort(key=lambda x: (
            self._natural_sort_key(x["aisle"]),
            self._natural_sort_key(x["shelf"]),
            self._natural_sort_key(x["bin"])
        ))

        return picking_items
