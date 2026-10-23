import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.identity.user_dto import (
    CreateUserCommand,
    DeleteUserCommand,
    UpdateOwnProfileCommand,
    UpdateUserCommand,
)
from app.application.identity.user_use_cases import CreateUser, DeleteUser, UpdateOwnProfile, UpdateUser
from app.application.shared.pagination import PaginatedResponse, PaginationParams, create_pagination_metadata
from app.domain.identity.errors import UserNotFoundError
from app.infrastructure.config import settings
from app.infrastructure.logging import get_logger
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.identity.user_repo import UserRepository
from app.presentation.api.v1.identity.deps import (
    actor_of,
    get_create_user,
    get_delete_user,
    get_update_own_profile,
    get_update_user,
)
from app.presentation.dependencies import get_current_tenant, get_current_user, require_permission
from app.presentation.schemas.identity.identity import UserCreate, UserOut, UserUpdate

logger = get_logger(__name__)
router = APIRouter()


def _enum_values(changes: dict) -> dict:
    """Los enums del schema viajan como texto plano hacia los casos de uso."""
    return {k: getattr(v, "value", v) for k, v in changes.items()}


async def _user_or_404(db: AsyncSession, user_id: int, tenant_id: int) -> User:
    user = await UserRepository(db).get_by_id(user_id, tenant_id=tenant_id)
    if not user:
        raise UserNotFoundError()
    return user


@router.get("/me", response_model=UserOut)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Obtiene el perfil del usuario actual"""
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    use_case: UpdateOwnProfile = Depends(get_update_own_profile),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza el perfil propio. Solo nombre, teléfono, avatar, correo y contraseña; los privilegios se ignoran."""
    await use_case.execute(
        UpdateOwnProfileCommand(actor_of(current_user), _enum_values(user_data.model_dump(exclude_unset=True)))
    )
    return await _user_or_404(db, current_user.id, current_user.tenant_id)


@router.post("/me/avatar", response_model=UserOut)
async def upload_current_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sube una foto de perfil para el usuario actual"""
    # Solo formatos raster permitidos (SVG se excluye: permite XSS al servirse desde /static)
    content_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    ext = content_types.get(file.content_type)
    if not ext:
        raise HTTPException(status_code=400, detail="Formato no permitido. Use JPG, PNG o WEBP")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"La imagen supera {settings.max_upload_size_mb} MB")

    os.makedirs("static/avatars", exist_ok=True)
    # La extensión sale de una lista cerrada, nunca del nombre enviado por el cliente
    filename = f"{current_user.id}_avatar{ext}"
    with open(os.path.join("static/avatars", filename), "wb") as buffer:
        buffer.write(content)

    repo = UserRepository(db)
    await repo.update(current_user.id, {"avatar_url": f"/static/avatars/{filename}"}, tenant_id=current_user.tenant_id)
    await db.commit()
    return await _user_or_404(db, current_user.id, current_user.tenant_id)


@router.get("/", response_model=PaginatedResponse[UserOut])
async def list_users(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Buscar por email o nombre"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users:view")),
):
    """Lista los usuarios del tenant (requiere 'users:view')"""
    items, total = await UserRepository(db).get_filtered(
        tenant_id=tenant_id, search=search, is_active=is_active,
        start_date=start_date, end_date=end_date, pagination=pagination,
    )
    return PaginatedResponse(items=items, metadata=create_pagination_metadata(pagination.page, pagination.page_size, total))


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission("users:create")),
    use_case: CreateUser = Depends(get_create_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea un usuario en el tenant. Nadie puede crear cuentas de mayor nivel que la suya."""
    user_id = await use_case.execute(
        CreateUserCommand(
            actor=actor_of(current_user),
            email=str(user_data.email),
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_admin=bool(user_data.is_admin),
            role=user_data.role.value,
            role_id=user_data.role_id,
        )
    )
    logger.info(f"Usuario creado: {user_id} en tenant {current_user.tenant_id}")
    return await _user_or_404(db, user_id, current_user.tenant_id)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("users:view")),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene un usuario por ID (requiere 'users:view')"""
    return await _user_or_404(db, user_id, current_user.tenant_id)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_permission("users:edit")),
    use_case: UpdateUser = Depends(get_update_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza un usuario (requiere 'users:edit'; no se pueden elevar privilegios ni cambiar los propios)"""
    await use_case.execute(
        UpdateUserCommand(actor_of(current_user), user_id, _enum_values(user_data.model_dump(exclude_unset=True)))
    )
    logger.info(f"Usuario actualizado: {user_id}")
    return await _user_or_404(db, user_id, current_user.tenant_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission("users:delete")),
    use_case: DeleteUser = Depends(get_delete_user),
):
    """Elimina un usuario (requiere 'users:delete')"""
    await use_case.execute(DeleteUserCommand(actor_of(current_user), user_id))
    logger.info(f"Usuario eliminado: {user_id}")
    return None
