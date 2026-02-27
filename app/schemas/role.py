from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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
