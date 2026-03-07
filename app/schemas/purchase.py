from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from .product import ProductOut
from .supplier import SupplierOut
from .user import UserOut
from ..models.purchase import PurchaseStatus, PurchasePaymentStatus

class PurchaseItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)

class PurchaseItemCreate(PurchaseItemBase):
    pass

class PurchaseItemOut(PurchaseItemBase):
    id: int
    subtotal: Decimal
    product: Optional[ProductOut] = None

    class Config:
        from_attributes = True

class PurchaseBase(BaseModel):
    supplier_id: int
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None

class PurchaseCreate(PurchaseBase):
    items: List[PurchaseItemCreate]

class PurchaseUpdate(BaseModel):
    supplier_id: Optional[int] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[PurchaseStatus] = None
    payment_status: Optional[PurchasePaymentStatus] = None
    due_date: Optional[datetime] = None

class PurchaseOut(PurchaseBase):
    id: int
    tenant_id: int
    user_id: Optional[int]
    total_amount: Decimal
    status: PurchaseStatus
    payment_status: PurchasePaymentStatus
    created_at: datetime
    updated_at: datetime
    
    user: Optional[UserOut] = None
    supplier: Optional[SupplierOut] = None  # Nota: Usamos el schema SupplierOut
    items: List[PurchaseItemOut]

    model_config = ConfigDict(from_attributes=True)

class PurchaseSummary(BaseModel):
    id: int
    supplier_name: Optional[str] = None
    total_amount: Decimal
    status: PurchaseStatus
    created_at: datetime

    class Config:
        from_attributes = True
