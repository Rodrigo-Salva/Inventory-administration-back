from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime

class ProductBatchBase(BaseModel):
    batch_number: str = Field(..., min_length=1, max_length=100)
    expiration_date: date
    initial_quantity: int = Field(default=0, ge=0)
    current_quantity: int = Field(default=0, ge=0)
    is_active: bool = True

class ProductBatchCreate(ProductBatchBase):
    product_id: int

class ProductBatchUpdate(BaseModel):
    batch_number: Optional[str] = Field(None, min_length=1, max_length=100)
    expiration_date: Optional[date] = None
    current_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

class ProductBatchOut(ProductBatchBase):
    id: int
    product_id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
