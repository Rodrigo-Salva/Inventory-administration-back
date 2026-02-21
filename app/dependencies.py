from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from .core.security import verify_token
from .models import get_db
from .repositories import UserRepository
from .models.user import User

security = HTTPBearer()

async def get_db_session(db: AsyncSession = Depends(get_db)):
    return db

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    payload = verify_token(credentials.credentials)
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload["user_id"])
    
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    
    if user.tenant_id != payload["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    
    return user

async def get_current_tenant(
    user: User = Depends(get_current_user)
) -> int:
    return user.tenant_id

async def get_current_admin(
    user: User = Depends(get_current_user)
) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required")
    return user