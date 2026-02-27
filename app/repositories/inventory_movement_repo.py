from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .base_repository import BaseRepository
from ..models import InventoryMovement, MovementType
from ..core.pagination import PaginationParams


class InventoryMovementRepository(BaseRepository[InventoryMovement]):
    """Repositorio para movimientos de inventario"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(InventoryMovement, db)
    
    async def get_by_product(
        self,
        product_id: int,
        tenant_id: int,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[InventoryMovement], int]:
        """Obtiene movimientos de un producto específico"""
        query = select(InventoryMovement).where(
            and_(
                InventoryMovement.tenant_id == tenant_id,
                InventoryMovement.product_id == product_id
            )
        ).options(
            selectinload(InventoryMovement.product),
            selectinload(InventoryMovement.user)
        ).order_by(InventoryMovement.created_at.desc())
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, InventoryMovement)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
    
    async def get_by_type(
        self,
        movement_type: MovementType,
        tenant_id: int,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[InventoryMovement], int]:
        """Obtiene movimientos por tipo"""
        query = select(InventoryMovement).where(
            and_(
                InventoryMovement.tenant_id == tenant_id,
                InventoryMovement.movement_type == movement_type
            )
        ).options(
            selectinload(InventoryMovement.product)
        ).order_by(InventoryMovement.created_at.desc())
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, InventoryMovement)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
    
    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        tenant_id: int,
        product_id: Optional[int] = None
    ) -> List[InventoryMovement]:
        """Obtiene movimientos en un rango de fechas"""
        conditions = [
            InventoryMovement.tenant_id == tenant_id,
            InventoryMovement.created_at >= start_date,
            InventoryMovement.created_at <= end_date
        ]
        
        if product_id:
            conditions.append(InventoryMovement.product_id == product_id)
        
        query = select(InventoryMovement).where(
            and_(*conditions)
        ).options(
            selectinload(InventoryMovement.product)
        ).order_by(InventoryMovement.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_recent_movements(
        self,
        tenant_id: int,
        days: int = 7,
        limit: int = 50
    ) -> List[InventoryMovement]:
        """Obtiene movimientos recientes"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(InventoryMovement).where(
            and_(
                InventoryMovement.tenant_id == tenant_id,
                InventoryMovement.created_at >= start_date
            )
        ).options(
            selectinload(InventoryMovement.product)
        ).order_by(InventoryMovement.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_total_value_by_type(
        self,
        movement_type: MovementType,
        tenant_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> float:
        """Calcula el valor total de movimientos por tipo"""
        conditions = [
            InventoryMovement.tenant_id == tenant_id,
            InventoryMovement.movement_type == movement_type,
            InventoryMovement.unit_cost.isnot(None)
        ]
        
        if start_date:
            conditions.append(InventoryMovement.created_at >= start_date)
        if end_date:
            conditions.append(InventoryMovement.created_at <= end_date)
        
        query = select(
            func.sum(func.abs(InventoryMovement.quantity) * InventoryMovement.unit_cost)
        ).where(and_(*conditions))
        
        result = await self.db.execute(query)
        return result.scalar() or 0.0

    async def get_filtered(
        self,
        tenant_id: int,
        product_id: Optional[int] = None,
        movement_type: Optional[MovementType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[InventoryMovement], int]:
        """Obtiene movimientos aplicando múltiples filtros para reportes"""
        conditions = [
            InventoryMovement.tenant_id == tenant_id
        ]
        
        if product_id:
            conditions.append(InventoryMovement.product_id == product_id)
            
        if movement_type:
            conditions.append(InventoryMovement.movement_type == movement_type)

        if start_date:
            conditions.append(InventoryMovement.created_at >= start_date)
            
        if end_date:
            conditions.append(InventoryMovement.created_at <= end_date)
            
        query = select(InventoryMovement).where(and_(*conditions)).options(
            selectinload(InventoryMovement.product),
            selectinload(InventoryMovement.user)
        ).order_by(InventoryMovement.created_at.desc())
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, InventoryMovement)
            
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
