from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from ..models.stock_transfer import StockTransferStatus
from .branch import BranchResponse
from .product import ProductOut

class StockTransferItemBase(BaseModel):
    product_id: int
    batch_id: Optional[int] = None
    quantity: int = Field(..., gt=0)

class StockTransferItemCreate(StockTransferItemBase):
    pass

class StockTransferItemOut(StockTransferItemBase):
    id: int
    product: Optional[ProductOut] = None
    model_config = ConfigDict(from_attributes=True)

class StockTransferBase(BaseModel):
    from_branch_id: int
    to_branch_id: int
    notes: Optional[str] = None
    reference: Optional[str] = None

class StockTransferCreate(StockTransferBase):
    items: List[StockTransferItemCreate]
    status: Optional[StockTransferStatus] = StockTransferStatus.PENDING

class StockTransferOut(StockTransferBase):
    id: int
    tenant_id: int
    user_id: int
    status: StockTransferStatus
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    from_branch: Optional[BranchResponse] = None
    to_branch: Optional[BranchResponse] = None
    items: List[StockTransferItemOut] = []
    
    model_config = ConfigDict(from_attributes=True)

class StockTransferUpdate(BaseModel):
    notes: Optional[str] = None
    reference: Optional[str] = None
