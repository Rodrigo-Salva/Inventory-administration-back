from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import os
import shutil

from ...models.base import get_db
from ...models import User
from ...dependencies import get_current_admin, get_current_tenant, get_current_user, require_role, require_permission
from ...models.user import User, UserRole
from ...repositories.user_repo import UserRepository
from ...schemas.user import UserCreate, UserUpdate, UserOut
from ...core.security import get_password_hash
from ...core.logging_config import get_logger
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata

logger = get_logger(__name__)
router = APIRouter()

@router.get("/me", response_model=UserOut)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Obtiene el perfil del usuario actual"""
    return current_user

@router.patch("/me", response_model=UserOut)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza el perfil del usuario actual"""
    repo = UserRepository(db)
    
    update_data = user_data.model_dump(exclude_unset=True)
    
    # No permitir cambiar is_admin o is_active a través de este endpoint
    update_data.pop("is_admin", None)
    update_data.pop("is_active", None)
    
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
    updated_user = await repo.update(current_user.id, update_data, tenant_id=current_user.tenant_id)
    await db.commit()
    await db.refresh(updated_user)
    
    return updated_user

@router.post("/me/avatar", response_model=UserOut)
async def upload_current_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sube una foto de perfil para el usuario actual"""
    # Validar tipo de archivo
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    
    # Crear directorio si no existe
    os.makedirs("static/avatars", exist_ok=True)
    
    # Nombre de archivo único: id_nombre.ext
    ext = os.path.splitext(file.filename)[1]
    if not ext:
        ext = ".png" # Fallback
        
    filename = f"{current_user.id}_avatar{ext}"
    file_path = os.path.join("static/avatars", filename)
    
    # Guardar archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # URL relativa para el frontend
    avatar_url = f"/static/avatars/{filename}"
    
    # Actualizar usuario en DB
    repo = UserRepository(db)
    updated_user = await repo.update(current_user.id, {"avatar_url": avatar_url}, tenant_id=current_user.tenant_id)
    await db.commit()
    await db.refresh(updated_user)
    
    return updated_user

@router.get("/", response_model=PaginatedResponse[UserOut])
async def list_users(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Buscar por email o nombre completo"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users:view"))
):
    """Lista todos los usuarios del tenant con paginación (Requiere permiso 'users:view')"""
    repo = UserRepository(db)
    
    items, total = await repo.get_filtered(
        tenant_id=tenant_id,
        search=search,
        is_active=is_active,
        start_date=start_date,
        end_date=end_date,
        pagination=pagination
    )
    
    metadata = create_pagination_metadata(pagination.page, pagination.page_size, total)
    return PaginatedResponse(items=items, metadata=metadata)

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users:create"))
):
    """Crea un nuevo usuario en el tenant (Requiere permiso 'users:create')"""
    repo = UserRepository(db)
    
    # Verificar email único globalmente
    existing = await repo.get_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump()
    user_dict["hashed_password"] = get_password_hash(user_dict.pop("password"))
    user_dict["tenant_id"] = tenant_id # Usar tenant_id de la dependencia get_current_tenant
    
    user = await repo.create(user_dict)
    await db.commit()
    await db.refresh(user)
    
    # Recargar con relaciones para cumplir el response_model UserOut
    user = await repo.get_by_id(user.id, tenant_id=tenant_id)
    
    logger.info(f"Usuario creado: {user.id} en tenant {user.tenant_id}")
    return user

@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un usuario por ID"""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("users:edit"))
):
    """Actualiza un usuario (Requiere permiso 'users:edit')"""
    repo = UserRepository(db)
    
    user = await repo.get_by_id(user_id, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_data.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
    updated_user = await repo.update(user_id, update_data, tenant_id=tenant_id)
    await db.commit()
    await db.refresh(updated_user)
    
    # Recargar con relaciones
    updated_user = await repo.get_by_id(updated_user.id, tenant_id=tenant_id)
    
    logger.info(f"Usuario actualizado: {user_id}")
    return updated_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("users:delete"))
):
    """Elimina un usuario (Requiere permiso 'users:delete')"""
    repo = UserRepository(db)
    
    user = await repo.get_by_id(user_id, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
    await repo.delete(user_id, tenant_id=tenant_id, soft=False)
    await db.commit()
    
    logger.info(f"Usuario eliminado: {user_id}")
    return None
