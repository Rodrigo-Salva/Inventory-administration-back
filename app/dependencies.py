from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from .core.security import verify_token
from .models import get_db
from .repositories import UserRepository

security = HTTPBearer()

async def get_db_session(db: AsyncSession = Depends(get_db)):
    return db

async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> int:
    payload = verify_token(credentials.credentials)
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload["user_id"])
    
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    
    if user.tenant_id != payload["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    
    return user.tenant_id