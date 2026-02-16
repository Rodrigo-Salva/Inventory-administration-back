from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from .base_repository import BaseRepository
from ..models import Supplier
from ..core.pagination import PaginationParams


class SupplierRepository(BaseRepository[Supplier]):
    """Repositorio para proveedores"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Supplier, db)
    
    async def get_by_code(self, code: str, tenant_id: int) -> Optional[Supplier]:
        """Obtiene un proveedor por código"""
        query = select(Supplier).where(
            and_(
                Supplier.code == code,
                Supplier.tenant_id == tenant_id,
                Supplier.is_deleted == False
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def search(
        self,
        search_term: str,
        tenant_id: int,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Supplier], int]:
        """Busca proveedores por nombre, código o email"""
        query = select(Supplier).where(
            and_(
                Supplier.tenant_id == tenant_id,
                Supplier.is_deleted == False,
                or_(
                    Supplier.name.ilike(f"%{search_term}%"),
                    Supplier.code.ilike(f"%{search_term}%"),
                    Supplier.email.ilike(f"%{search_term}%") if search_term else False
                )
            )
        )
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, Supplier)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
    
    async def get_active_suppliers(self, tenant_id: int) -> List[Supplier]:
        """Obtiene proveedores activos"""
        query = select(Supplier).where(
            and_(
                Supplier.tenant_id == tenant_id,
                Supplier.is_active == 1,
                Supplier.is_deleted == False
            )
        ).order_by(Supplier.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
