from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from app.infrastructure.persistence.repositories.base_repository import BaseRepository
from app.infrastructure.persistence.models.purchasing.purchase import Purchase, PurchaseItem, PurchaseStatus
from app.application.shared.pagination import PaginationParams

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

    async def get_stats(self, tenant_id: int) -> dict:
        """Calcula estadísticas generales de compras para el tenant"""
        conditions = [Purchase.tenant_id == tenant_id]
        
        # 1. Totales por estado y montos
        query = select(
            func.count(Purchase.id).label("total_count"),
            func.sum(Purchase.total_amount).label("total_amount"),
            func.count(Purchase.id).filter(Purchase.status == PurchaseStatus.DRAFT).label("draft_count"),
            func.count(Purchase.id).filter(Purchase.status == PurchaseStatus.RECEIVED).label("received_count"),
            func.sum(Purchase.total_amount).filter(Purchase.status == PurchaseStatus.RECEIVED).label("received_amount")
        ).where(Purchase.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        row = result.fetchone()
        
        return {
            "total_count": row.total_count or 0,
            "total_amount": float(row.total_amount or 0),
            "draft_count": row.draft_count or 0,
            "received_count": row.received_count or 0,
            "received_amount": float(row.received_amount or 0)
        }
