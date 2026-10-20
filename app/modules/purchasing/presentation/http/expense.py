from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class ExpenseCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass

class ExpenseCategoryResponse(ExpenseCategoryBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ExpenseBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: str
    category_id: Optional[int] = None
    cash_session_id: Optional[int] = None
    expense_date: Optional[datetime] = None

class ExpenseCreate(ExpenseBase):
    category_id: int

class ExpenseResponse(ExpenseBase):
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    created_at: datetime
    
    category: Optional[ExpenseCategoryResponse] = None

    class Config:
        from_attributes = True

class ExpenseSummary(BaseModel):
    items: List[ExpenseResponse]
    total: int
    page: int
    size: int
