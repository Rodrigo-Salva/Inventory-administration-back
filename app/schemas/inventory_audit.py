from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .product import ProductOut

class InventoryAuditItemBase(BaseModel):
    product_id: int
    counted_stock: int = Field(..., ge=0)
    notes: Optional[str] = None

class InventoryAuditItemCreate(InventoryAuditItemBase):
    pass

class InventoryAuditItemOut(InventoryAuditItemBase):
    id: int
    audit_id: int
    expected_stock: int
    difference: int
    is_adjusted: bool
    product: Optional[ProductOut] = None
    created_at: datetime

    class Config:
        from_attributes = True

class InventoryAuditBase(BaseModel):
    branch_id: int
    notes: Optional[str] = None

class InventoryAuditCreate(InventoryAuditBase):
    pass

class InventoryAuditOut(InventoryAuditBase):
    id: int
    tenant_id: int
    user_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    items: List[InventoryAuditItemOut] = []

    class Config:
        from_attributes = True
