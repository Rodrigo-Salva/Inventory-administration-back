from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.infrastructure.persistence.models.inventory.adjustment import AdjustmentReason

class AdjustmentBase(BaseModel):
    product_id: int
    adjustment_type: str  # "IN" or "OUT"
    quantity: float
    reason: AdjustmentReason
    notes: Optional[str] = None

class AdjustmentCreate(AdjustmentBase):
    branch_id: Optional[int] = None  # por defecto, la sucursal del usuario

class AdjustmentOut(AdjustmentBase):
    id: int
    user_id: int
    tenant_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
