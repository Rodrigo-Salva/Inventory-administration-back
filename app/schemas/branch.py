from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class BranchBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    is_active: bool = True

class BranchCreate(BranchBase):
    pass

class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

class BranchResponse(BranchBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schemas para el manejo de stock por sucursal
class ProductBranchBase(BaseModel):
    branch_id: int
    stock: int = 0
    min_stock: int = 10
    max_stock: Optional[int] = None

class ProductBranchUpdate(BaseModel):
    stock: Optional[int] = None
    min_stock: Optional[int] = None
    max_stock: Optional[int] = None

class ProductBranchResponse(ProductBranchBase):
    id: int
    product_id: int
    branch: BranchResponse
    
    class Config:
        from_attributes = True
