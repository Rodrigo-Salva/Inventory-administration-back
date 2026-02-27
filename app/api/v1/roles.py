from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...models import get_db, User
from ...dependencies import get_current_admin, require_permission, get_current_user, get_current_tenant
from ...schemas.role import RoleOut, RoleCreate, RoleUpdate, PermissionOut
from ...repositories.role_repo import RoleRepository

router = APIRouter(tags=["Roles & Permissions"])

@router.get("/permissions", response_model=List[PermissionOut])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """Lista todos los permisos disponibles en el sistema"""
    repo = RoleRepository(db)
    return await repo.get_all_permissions()

@router.get("/", response_model=List[RoleOut])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """Lista todos los roles del tenant"""
    repo = RoleRepository(db)
    return await repo.get_roles_by_tenant(current_user.tenant_id)

@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """Crea un nuevo rol personalizado"""
    repo = RoleRepository(db)
    role_data = role_in.model_dump(exclude={"permission_ids"})
    new_role = await repo.create_role(current_user.tenant_id, role_data, role_in.permission_ids)
    await db.commit()
    await db.refresh(new_role)
    return new_role

@router.put("/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """Actualiza un rol y sus permisos"""
    repo = RoleRepository(db)
    role_data = role_in.model_dump(exclude={"permission_ids"}, exclude_unset=True)
    updated_role = await repo.update_role(role_id, current_user.tenant_id, role_data, role_in.permission_ids)
    
    if not updated_role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    await db.commit()
    await db.refresh(updated_role)
    return updated_role

@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """Elimina un rol (si no es del sistema)"""
    repo = RoleRepository(db)
    role = await repo.get_by_id(role_id)
    
    if not role or role.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Role not found")
        
    # Permitimos eliminar incluso roles del sistema si el usuario lo desea
    # (El frontend avisará que es una acción crítica)
        
    await repo.delete(role_id)
    await db.commit()
    return {"message": "Role deleted"}
