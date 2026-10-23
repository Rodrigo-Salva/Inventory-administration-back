from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

class CashSessionBase(BaseModel):
    opening_balance: Decimal = Field(..., ge=0)
    notes: Optional[str] = None

class CashSessionCreate(CashSessionBase):
    pass

class CashSessionClose(BaseModel):
    closing_balance: Decimal = Field(..., ge=0)

class CashSessionResponse(CashSessionBase):
    id: int
    tenant_id: int
    user_id: int
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    expected_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None

    class Config:
        from_attributes = True
