from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from ..models.sale import PaymentMethod

class PaymentBase(BaseModel):
    amount: Decimal = Field(..., description="Monto del abono")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    notes: Optional[str] = None

class PaymentCreate(PaymentBase):
    credit_id: int

class PaymentOut(PaymentBase):
    id: int
    credit_id: int
    tenant_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}

class CreditBase(BaseModel):
    total_amount: Decimal
    remaining_amount: Decimal
    status: str
    due_date: Optional[datetime] = None

class CreditOut(CreditBase):
    id: int
    tenant_id: int
    customer_id: int
    sale_id: int
    created_at: datetime
    
    # Podríamos incluir los pagos si es necesario
    payments: List[PaymentOut] = []
    
    model_config = {"from_attributes": True}

class CreditSummary(BaseModel):
    id: int
    sale_id: int
    total_amount: Decimal
    remaining_amount: Decimal
    status: str
    due_date: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
