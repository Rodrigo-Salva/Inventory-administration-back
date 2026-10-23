from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.infrastructure.persistence.models.identity.user import UserRole


class PermissionOut(BaseModel):
    id: int
    name: str
    codename: str
    module: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class RoleOut(RoleBase):
    id: int
    tenant_id: int
    is_system: bool
    permissions: List[PermissionOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class TenantBase(BaseModel):
    name: str
    subdomain: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    monthly_sales_goal: Optional[float] = 0.0


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    monthly_sales_goal: Optional[float] = None


class TenantOut(TenantBase):
    id: int
    plan: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: Optional[bool] = False
    role: UserRole = UserRole.SELLER
    role_id: Optional[int] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
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
