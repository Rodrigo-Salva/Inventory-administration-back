from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from .core.security import verify_token
from .models import get_db
from .repositories import UserRepository
from .models.user import User, UserRole

security = HTTPBearer()

async def get_db_session(db: AsyncSession = Depends(get_db)):
    return db

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    payload = verify_token(credentials.credentials)
    
    # Usamos carga anticipada (eager loading) para el rol y los permisos
    # Esto es CRÍTICIO para que el frontend reciba los permisos y los respete
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from .models.role import Role
    
    query = select(User).where(User.id == payload["user_id"]).options(
        selectinload(User.role_obj).selectinload(Role.permissions)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    
    if user.tenant_id != payload["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    
    return user

async def get_current_tenant(
    user: User = Depends(get_current_user)
) -> int:
    return user.tenant_id

def require_permission(codename: str):
    """Dependencia para requerir un permiso específico (ej: 'products:create')"""
    async def permission_checker(user: User = Depends(get_current_user)) -> User:
        # Superadmin tiene todo
        if user.role == UserRole.SUPERADMIN:
            return user
            
        # Dueño del tenant (is_admin=True sin rol asignado o con rol ADMIN pero sin permisos cargados)
        # Si tiene un rol asignado, DEBEMOS respetar los permisos de ese rol.
        if user.is_admin and not user.role_obj:
            return user

        # Obtener codenames de los permisos del rol
        permissions = []
        if user.role_obj and user.role_obj.permissions:
            permissions = [p.codename for p in user.role_obj.permissions]
            
        if codename not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Permiso insuficiente: se requiere '{codename}'"
            )
        return user
    return permission_checker

def require_role(allowed_roles: list[UserRole]):
    """Dependencia para requerir uno de los roles permitidos"""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        # Superadmin siempre tiene acceso
        if user.role == UserRole.SUPERADMIN:
            return user
            
        # Dueño del tenant bypass
        if user.is_admin and not user.role_obj:
            return user

        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Permisos insuficientes. Se requiere uno de: {[r.value for r in allowed_roles]}"
            )
        return user
    return role_checker

async def get_current_admin(
    user: User = Depends(get_current_user)
) -> User:
    # Verificamos si es admin global o tiene el rol ADMIN
    if user.role == UserRole.SUPERADMIN:
        return user
        
    if user.role == UserRole.ADMIN or (user.role_obj and user.role_obj.name == "ADMIN"):
        return user
        
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")