from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date as date_obj, datetime

class ExpenseBase(BaseModel):
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    date: date_obj
    reference: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    date: Optional[date_obj] = None
    reference: Optional[str] = None

class ExpenseOut(ExpenseBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

class PaginatedExpenses(BaseModel):
    items: List[ExpenseOut]
    total: int
    page: int
    size: int

class TimeSeriesPoint(BaseModel):
    date: str
    amount: float

class ExpenseStats(BaseModel):
    category_totals: dict[str, float]
    total_amount: float
    daily_stats: List[TimeSeriesPoint] = []
    weekly_stats: List[TimeSeriesPoint] = []
    monthly_stats: List[TimeSeriesPoint] = []
