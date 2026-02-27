from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .base_repository import BaseRepository
from ..models import User, Role
from ..core.pagination import PaginationParams

class UserRepository(BaseRepository[User]):
    """Repositorio para usuarios"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def get_by_id(self, id: int, tenant_id: Optional[int] = None) -> Optional[User]:
        query = select(User).where(User.id == id).options(
            selectinload(User.role_obj).selectinload(Role.permissions)
        )
        if tenant_id is not None:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Obtiene un usuario por email con su rol y permisos"""
        query = select(User).where(User.email == email).options(
            selectinload(User.role_obj).selectinload(Role.permissions)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        tenant_id: int,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[User], int]:
        """Obtiene usuarios aplicando filtros de búsqueda, estado y fecha"""
        conditions = [
            User.tenant_id == tenant_id,
        ]
        
        if search:
            conditions.append(or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%") if hasattr(User, 'full_name') else False
            ))
            
        if is_active is not None:
            conditions.append(User.is_active == is_active)

        if start_date:
            conditions.append(User.created_at >= start_date)
            
        if end_date:
            conditions.append(User.created_at <= end_date)
            
        query = select(User).where(and_(*conditions)).options(
            selectinload(User.role_obj).selectinload(Role.permissions)
        ).order_by(User.email.asc())
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, User)
            
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
