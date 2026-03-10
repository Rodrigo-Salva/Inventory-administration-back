from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from .base_repository import BaseRepository
from ..models.branch import Branch
from ..core.pagination import PaginationParams

class BranchRepository(BaseRepository[Branch]):
    """Repositorio para sucursales"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Branch, db)

    async def get_all_active(self, tenant_id: int) -> List[Branch]:
        """Obtiene todas las sucursales activas de un tenant"""
        query = select(Branch).where(
            and_(
                Branch.tenant_id == tenant_id,
                Branch.is_active == True,
                Branch.is_deleted == False
            )
        ).order_by(Branch.name.asc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_paginated(
        self,
        pagination: PaginationParams,
        tenant_id: int
    ) -> tuple[List[Branch], int]:
        """Obtiene sucursales paginadas para un tenant"""
        query = select(Branch).where(
            and_(
                Branch.tenant_id == tenant_id,
                Branch.is_deleted == False
            )
        ).order_by(Branch.created_at.desc())
        
        from ..core.pagination import paginate
        return await paginate(self.db, query, pagination, Branch)
