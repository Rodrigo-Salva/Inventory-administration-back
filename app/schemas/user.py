from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from ..models.user import UserRole

from .role import RoleOut

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: Optional[bool] = False
    role: UserRole = UserRole.SELLER
    role_id: Optional[int] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    role_id: Optional[int] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: bool
    role: UserRole
    role_id: Optional[int] = None
    role_obj: Optional[RoleOut] = None
    is_active: bool
    tenant_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True