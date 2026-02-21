from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.base import get_db
from ...dependencies import get_current_admin, get_current_tenant
from ...repositories.user_repo import UserRepository
from ...schemas.user import UserCreate, UserUpdate, UserOut
from ...core.security import get_password_hash
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("", response_model=List[UserOut])
async def list_users(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los usuarios del tenant"""
    repo = UserRepository(db)
    users = await repo.get_all(tenant_id=tenant_id)
    return users

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_admin: int = Depends(get_current_admin), # Solo admins pueden crear users
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo usuario en el tenant"""
    repo = UserRepository(db)
    
    # Verificar email único globalmente (o por tenant si se prefiere, pero el modelo dice unique=True)
    existing = await repo.get_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump()
    user_dict["hashed_password"] = get_password_hash(user_dict.pop("password"))
    user_dict["tenant_id"] = current_admin.tenant_id
    
    user = await repo.create(user_dict)
    await db.commit()
    await db.refresh(user)
    
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
    current_admin: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza un usuario"""
    repo = UserRepository(db)
    
    user = await repo.get_by_id(user_id, tenant_id=current_admin.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_data.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
    updated_user = await repo.update(user_id, update_data, tenant_id=current_admin.tenant_id)
    await db.commit()
    
    logger.info(f"Usuario actualizado: {user_id}")
    return updated_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_admin: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Elimina un usuario (hard delete por ahora o soft delete si el repo lo soporta)"""
    repo = UserRepository(db)
    
    user = await repo.get_by_id(user_id, tenant_id=current_admin.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
    await repo.delete(user_id, tenant_id=current_admin.tenant_id, soft=False)
    await db.commit()
    
    logger.info(f"Usuario eliminado: {user_id}")
    return None
