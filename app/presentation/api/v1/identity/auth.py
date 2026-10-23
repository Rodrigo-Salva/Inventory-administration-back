from datetime import timedelta
from typing import Dict

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config import settings
from app.infrastructure.security.rate_limit import AUTH_LIMIT, limiter
from app.infrastructure.security.auth import create_access_token
from app.infrastructure.persistence.database import get_db
from app.application.identity.use_cases import AuthenticateUser, EmailAlreadyRegisteredError, RegisterTenantOwner, RegisterTenantOwnerCommand
from app.infrastructure.security.password_hasher import PasslibPasswordHasher
from app.infrastructure.persistence.repositories.identity.identity_repo import SqlAlchemyIdentityRepository
from app.presentation.schemas.identity.identity import UserCreate

router = APIRouter()


class RegisterTenantRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


def _use_cases(db: AsyncSession) -> tuple[RegisterTenantOwner, AuthenticateUser]:
    repository = SqlAlchemyIdentityRepository(db)
    passwords = PasslibPasswordHasher()
    return RegisterTenantOwner(repository, passwords), AuthenticateUser(repository, passwords)


@router.post("/register", response_model=Dict)
@limiter.limit(AUTH_LIMIT)
async def register_tenant(
    request: Request, payload: RegisterTenantRequest, db: AsyncSession = Depends(get_db)
):
    register, _ = _use_cases(db)
    try:
        owner = await register.execute(
            RegisterTenantOwnerCommand(email=str(payload.email), password=payload.password)
        )
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(status_code=400, detail="Email already registered") from error

    token = create_access_token(
        {"user_id": owner.user_id, "tenant_id": owner.tenant_id},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {
        "message": "Tenant created successfully",
        "tenant_id": owner.tenant_id,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/login", response_model=Dict)
@limiter.limit(AUTH_LIMIT)
async def login(
    request: Request, username: str = Form(), password: str = Form(), db: AsyncSession = Depends(get_db)
):
    _, authenticate = _use_cases(db)
    identity = await authenticate.execute(username, password)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        {"user_id": identity.id, "tenant_id": identity.tenant_id},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {"access_token": token, "token_type": "bearer", "tenant_id": identity.tenant_id}
