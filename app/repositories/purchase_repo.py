from typing import List, Optional, Tuple
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from .base_repository import BaseRepository
from ..models.purchase import Purchase, PurchaseItem, PurchaseStatus
from ..models.product import Product
from ..models.inventory_movement import InventoryMovement
from ..core.pagination import PaginationParams

class PurchaseRepository(BaseRepository[Purchase]):
    def __init__(self, db):
        super().__init__(Purchase, db)

    async def get_with_items(self, purchase_id: int, tenant_id: int) -> Optional[Purchase]:
        """Obtiene una compra con sus ítems y productos cargados"""
        result = await self.db.execute(
            select(Purchase)
            .where(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id)
            .options(
                selectinload(Purchase.items).selectinload(PurchaseItem.product),
                selectinload(Purchase.supplier),
                selectinload(Purchase.user)
            )
        )
        return result.scalars().first()

    async def get_filtered(
        self, 
        tenant_id: int, 
        status: Optional[PurchaseStatus] = None,
        supplier_id: Optional[int] = None,
        pagination: PaginationParams = PaginationParams()
    ) -> Tuple[List[Purchase], int]:
        """Lista compras con filtros y paginación"""
        query = select(Purchase).where(Purchase.tenant_id == tenant_id)
        
        if status:
            query = query.where(Purchase.status == status)
        if supplier_id:
            query = query.where(Purchase.supplier_id == supplier_id)
            
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.execute(count_query)
        total_count = total.scalar() or 0
        
        # Paginar y ordenar por fecha descendente
        query = query.order_by(desc(Purchase.created_at)).offset(pagination.offset).limit(pagination.page_size)
        query = query.options(selectinload(Purchase.supplier))
        
        result = await self.db.execute(query)
        return list(result.scalars().all()), total_count

    async def receive_purchase(self, purchase_id: int, tenant_id: int) -> Optional[Purchase]:
        """
        Marca una compra como recibida y actualiza el stock de los productos.
        Este método debe ser llamado dentro de un contexto de transacción si es posible,
        o asegurar commit externo.
        """
        purchase = await self.get_with_items(purchase_id, tenant_id)
        if not purchase or purchase.status != PurchaseStatus.DRAFT:
            return None

        for item in purchase.items:
            product = item.product
            if not product:
                continue

            # 1. Registrar movimiento de inventario
            movement = InventoryMovement(
                tenant_id=tenant_id,
                product_id=product.id,
                movement_type="entry",
                quantity=item.quantity,
                stock_before=product.stock,
                stock_after=product.stock + item.quantity,
                unit_cost=item.unit_cost,
                reference=f"Compra #{purchase.id} {purchase.reference_number or ''}",
                notes=f"Recepción de compra automatizada"
            )
            self.db.add(movement)

            # 2. Actualizar stock y costo del producto
            product.stock += item.quantity
            product.cost = item.unit_cost  # Actualizamos al último costo de compra
        
        # 3. Cambiar estado de la compra
        purchase.status = PurchaseStatus.RECEIVED
        
        await self.db.flush() # Sincronizar cambios antes de retornar
        return purchase
