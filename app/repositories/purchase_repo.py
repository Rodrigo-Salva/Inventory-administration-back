from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from .base_repository import BaseRepository
from ..models.purchase import Purchase, PurchaseItem, PurchaseStatus
from ..models.product import Product
from ..models.inventory_movement import InventoryMovement
from ..core.pagination import PaginationParams
from ..services.inventory_service import InventoryService

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
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        pagination: PaginationParams = PaginationParams()
    ) -> Tuple[List[Purchase], int]:
        """Lista compras con filtros y paginación"""
        from sqlalchemy import and_, or_
        conditions = [Purchase.tenant_id == tenant_id]
        
        if status:
            conditions.append(Purchase.status == status)
        if supplier_id:
            conditions.append(Purchase.supplier_id == supplier_id)
        if start_date:
            conditions.append(Purchase.created_at >= start_date)
        if end_date:
            conditions.append(Purchase.created_at <= end_date)
            
        if search:
            conditions.append(or_(
                Purchase.reference_number.ilike(f"%{search}%"),
                Purchase.notes.ilike(f"%{search}%")
            ))
            
        query = select(Purchase).where(and_(*conditions))
            
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.execute(count_query)
        total_count = total.scalar() or 0
        
        # Paginar y ordenar por fecha descendente
        query = query.order_by(desc(Purchase.created_at)).offset(pagination.offset).limit(pagination.page_size)
        query = query.options(
            selectinload(Purchase.supplier),
            selectinload(Purchase.user),
            selectinload(Purchase.items).selectinload(PurchaseItem.product)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all()), total_count

    async def receive_purchase(self, purchase_id: int, tenant_id: int) -> Optional[Purchase]:
        """
        Marca una compra como recibida y actualiza el stock de los productos usando InventoryService
        """
        purchase = await self.get_with_items(purchase_id, tenant_id)
        if not purchase or purchase.status != PurchaseStatus.DRAFT:
            return None

        inv_service = InventoryService(self.db)
        
        for item in purchase.items:
            product = item.product
            if not product:
                continue

            # 1. Usar InventoryService para registrar la entrada en la sucursal correcta
            await inv_service.add_stock(
                product_id=product.id,
                branch_id=purchase.branch_id,
                quantity=item.quantity,
                tenant_id=tenant_id,
                user_id=purchase.user_id,
                unit_cost=item.unit_cost,
                reference=f"Compra #{purchase.id} {purchase.reference_number or ''}",
                notes="Recepción de compra automatizada"
            )

            # 2. Actualizar costo del producto
            product.cost = item.unit_cost  # Actualizamos al último costo de compra
        
        # 3. Cambiar estado de la compra
        purchase.status = PurchaseStatus.RECEIVED
        
        await self.db.flush() # Sincronizar cambios antes de retornar
        return purchase
