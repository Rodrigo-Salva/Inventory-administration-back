from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .base_repository import BaseRepository
from ..models import Category
from ..core.pagination import PaginationParams


class CategoryRepository(BaseRepository[Category]):
    """Repositorio para categorías"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Category, db)
    
    async def get_by_code(self, code: str, tenant_id: int) -> Optional[Category]:
        """Obtiene una categoría por código"""
        query = select(Category).where(
            and_(
                Category.code == code,
                Category.tenant_id == tenant_id,
                Category.is_deleted == False
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_root_categories(self, tenant_id: int) -> List[Category]:
        """Obtiene categorías raíz (sin padre)"""
        query = select(Category).where(
            and_(
                Category.tenant_id == tenant_id,
                Category.parent_id.is_(None),
                Category.is_deleted == False
            )
        ).order_by(Category.display_order, Category.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_children(self, parent_id: int, tenant_id: int) -> List[Category]:
        """Obtiene subcategorías de una categoría padre"""
        query = select(Category).where(
            and_(
                Category.tenant_id == tenant_id,
                Category.parent_id == parent_id,
                Category.is_deleted == False
            )
        ).order_by(Category.display_order, Category.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_with_children(self, category_id: int, tenant_id: int) -> Optional[Category]:
        """Obtiene una categoría con sus hijos cargados"""
        query = select(Category).where(
            and_(
                Category.id == category_id,
                Category.tenant_id == tenant_id,
                Category.is_deleted == False
            )
        ).options(selectinload(Category.children))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_hierarchy(self, tenant_id: int) -> List[Category]:
        """Obtiene toda la jerarquía de categorías"""
        query = select(Category).where(
            and_(
                Category.tenant_id == tenant_id,
                Category.is_deleted == False
            )
        ).options(
            selectinload(Category.children),
            selectinload(Category.parent)
        ).order_by(Category.parent_id.nullsfirst(), Category.display_order, Category.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_filtered(
        self,
        tenant_id: int,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Category], int]:
        """Obtiene categorías aplicando filtros de búsqueda y estado"""
        conditions = [
            Category.tenant_id == tenant_id,
            Category.is_deleted == False
        ]
        
        if search:
            conditions.append(or_(
                Category.name.ilike(f"%{search}%"),
                Category.code.ilike(f"%{search}%")
            ))
            
        if is_active is not None:
            conditions.append(Category.is_active == is_active)

        if start_date:
            conditions.append(Category.created_at >= start_date)
            
        if end_date:
            conditions.append(Category.created_at <= end_date)
            
        query = select(Category).where(and_(*conditions)).order_by(Category.name.asc())
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, Category)
            
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
