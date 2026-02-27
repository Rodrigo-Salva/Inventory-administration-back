from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from .base_repository import BaseRepository
from ..models.role import Role, Permission, role_permissions

class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_all_permissions(self) -> List[Permission]:
        result = await self.db.execute(select(Permission))
        return result.scalars().all()

    async def get_roles_by_tenant(self, tenant_id: int) -> List[Role]:
        query = select(Role).where(Role.tenant_id == tenant_id).options(selectinload(Role.permissions))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_role_with_permissions(self, role_id: int, tenant_id: int) -> Optional[Role]:
        query = select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id).options(selectinload(Role.permissions))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_role(self, tenant_id: int, role_data: dict, permission_ids: List[int]) -> Role:
        role = Role(tenant_id=tenant_id, name=role_data["name"], description=role_data.get("description"))
        if permission_ids:
            perms = await self.db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
            role.permissions = perms.scalars().all()
        
        self.db.add(role)
        return role

    async def update_role(self, role_id: int, tenant_id: int, role_data: dict, permission_ids: Optional[List[int]] = None) -> Optional[Role]:
        role = await self.get_role_with_permissions(role_id, tenant_id)
        if not role:
            return None
        
        for key, value in role_data.items():
            setattr(role, key, value)
            
        if permission_ids is not None:
            perms = await self.db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
            role.permissions = perms.scalars().all()
            
        return role
