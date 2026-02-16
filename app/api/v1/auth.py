from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr
from typing import Dict
from datetime import timedelta

from ...core.security import get_password_hash, verify_password, create_access_token
from ...core.config import settings
from ...dependencies import get_current_tenant, get_db_session
from ...models import get_db, User, Tenant
from ...repositories import UserRepository
from ...schemas.user import UserCreate, UserOut

router = APIRouter()

@router.post("/register", response_model=Dict)
async def register_tenant(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Verifica email único
    user_repo = UserRepository(db)
    existing = await user_repo.get_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Crea tenant + primer user (admin)
    tenant = Tenant(name=f"Tenant-{user_data.email.split('@')[0]}")
    db.add(tenant)
    await db.flush()  # Obtiene ID
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        tenant_id=tenant.id,
        is_admin=True
    )
    db.add(user)
    await db.commit()
    
    token = create_access_token(
        {"user_id": user.id, "tenant_id": tenant.id},
        timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return {
        "message": "Tenant created successfully",
        "tenant_id": tenant.id,
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/login", response_model=Dict)
async def login(
    username: str = Form(),  # Form data
    password: str = Form(),  # Form data
    db: AsyncSession = Depends(get_db)
):
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(username)  # username es el email
        
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = create_access_token({"user_id": user.id, "tenant_id": user.tenant_id})
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "tenant_id": user.tenant_id
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR EN LOGIN: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )