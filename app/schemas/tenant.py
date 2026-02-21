from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

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

class TenantOut(TenantBase):
    id: int
    plan: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
