from pydantic import BaseModel, Field
from typing import List, Optional
from .product import ProductOut
from .user import UserOut
from datetime import datetime
from decimal import Decimal

class SaleItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal

class SaleItemCreate(SaleItemBase):
    pass

class SaleItemResponse(SaleItemBase):
    id: int
    subtotal: Decimal
    product_name: Optional[str] = None
    product: Optional[ProductOut] = None

    class Config:
        from_attributes = True

class SaleBase(BaseModel):
    payment_method: str = "cash"
    status: str = "completed"
    notes: Optional[str] = None

class SaleCreate(SaleBase):
    items: List[SaleItemCreate]

class SaleResponse(SaleBase):
    id: int
    tenant_id: int
    user_id: Optional[int]
    total_amount: Decimal
    created_at: datetime
    user: Optional[UserOut] = None
    items: List[SaleItemResponse]

    class Config:
        from_attributes = True

class PaginatedSaleResponse(BaseModel):
    items: List[SaleResponse]
    total: int
    page: int
    size: int
    pages: int
