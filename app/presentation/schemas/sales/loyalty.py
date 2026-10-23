from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional

class LoyaltyConfigBase(BaseModel):
    points_per_amount: Decimal = Field(..., description="Dinero gastado por cada punto generado")
    amount_per_point: Decimal = Field(..., description="Valor en dinero de cada punto")
    is_active: bool = True
    min_redemption_points: int = 0

class LoyaltyConfigCreate(LoyaltyConfigBase):
    pass

class LoyaltyConfigUpdate(BaseModel):
    points_per_amount: Optional[Decimal] = None
    amount_per_point: Optional[Decimal] = None
    is_active: Optional[bool] = None
    min_redemption_points: Optional[int] = None

class LoyaltyConfig(LoyaltyConfigBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LoyaltyTransactionBase(BaseModel):
    customer_id: int
    points: int
    description: Optional[str] = None
    transaction_type: str # earn, redeem, adjust

class LoyaltyTransactionCreate(LoyaltyTransactionBase):
    sale_id: Optional[int] = None

class LoyaltyTransaction(LoyaltyTransactionBase):
    id: int
    tenant_id: int
    sale_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
