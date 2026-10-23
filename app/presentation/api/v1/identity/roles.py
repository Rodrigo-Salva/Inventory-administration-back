from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.identity.user_dto import CreateRoleCommand, DeleteRoleCommand, UpdateRoleCommand
from app.application.identity.user_use_cases import CreateRole, DeleteRole, UpdateRole
from app.domain.identity.errors import RoleNotFoundError
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.identity.role_repo import RoleRepository
from app.presentation.api.v1.identity.deps import get_create_role, get_delete_role, get_update_role
from app.presentation.dependencies import require_permission
from app.presentation.schemas.identity.identity import PermissionOut, RoleCreate, RoleOut, RoleUpdate

router = APIRouter(tags=["Roles & Permissions"])


async def _role_or_404(db: AsyncSession, role_id: int, tenant_id: int):
    role = await RoleRepository(db).get_role_with_permissions(role_id, tenant_id)
    if not role:
        raise RoleNotFoundError()
    return role


@router.get("/permissions", response_model=List[PermissionOut])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage")),
):
    """Lista todos los permisos disponibles en el sistema"""
    return await RoleRepository(db).get_all_permissions()


@router.get("/", response_model=List[RoleOut])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage")),
):
    """Lista todos los roles del tenant"""
    return await RoleRepository(db).get_roles_by_tenant(current_user.tenant_id)


@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    use_case: CreateRole = Depends(get_create_role),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage")),
):
    """Crea un nuevo rol personalizado"""
    role_id = await use_case.execute(
        CreateRoleCommand(
            current_user.tenant_id, role_in.name, role_in.description, tuple(role_in.permission_ids)
        )
    )
    return await _role_or_404(db, role_id, current_user.tenant_id)


@router.put("/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    use_case: UpdateRole = Depends(get_update_role),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage")),
):
    """Actualiza un rol y sus permisos"""
    permission_ids = None if role_in.permission_ids is None else tuple(role_in.permission_ids)
    await use_case.execute(
        UpdateRoleCommand(
            current_user.tenant_id, role_id,
            role_in.model_dump(exclude={"permission_ids"}, exclude_unset=True), permission_ids,
        )
    )
    return await _role_or_404(db, role_id, current_user.tenant_id)


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    use_case: DeleteRole = Depends(get_delete_role),
    current_user: User = Depends(require_permission("roles:manage")),
):
    """Elimina un rol (si no está asignado a usuarios)"""
    await use_case.execute(DeleteRoleCommand(current_user.tenant_id, role_id))
    return {"message": "Role deleted"}
