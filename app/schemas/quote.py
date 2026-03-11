from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import date, datetime
from app.models.quote import QuoteStatus
from app.core.pagination import PageMetadata

class QuoteItemBase(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)

class QuoteItemCreate(QuoteItemBase):
    pass

class QuoteItemResponse(QuoteItemBase):
    id: int
    quote_id: int
    subtotal: float

    model_config = ConfigDict(from_attributes=True)

class QuoteBase(BaseModel):
    customer_id: Optional[int] = None
    valid_until: date
    notes: Optional[str] = None

class QuoteCreate(QuoteBase):
    items: List[QuoteItemCreate]

class QuoteResponse(QuoteBase):
    id: int
    tenant_id: int
    user_id: Optional[int]
    total_amount: float
    status: QuoteStatus
    sale_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    items: List[QuoteItemResponse]

    model_config = ConfigDict(from_attributes=True)

class PaginatedQuoteResponse(BaseModel):
    items: List[QuoteResponse]
    metadata: PageMetadata
