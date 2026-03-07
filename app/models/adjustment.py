import enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, ForeignKey, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, TenantMixin

class AdjustmentReason(str, enum.Enum):
    DAMAGE = "DAMAGE"
    LOSS = "LOSS"
    CORRECTION = "CORRECTION"
    INTERNAL_USE = "INTERNAL_USE"

class InventoryAdjustment(Base, TimestampMixin, TenantMixin):
    __tablename__ = "inventory_adjustments"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # "IN" for addition, "OUT" for subtraction
    adjustment_type = Column(String(10), nullable=False) 
    quantity = Column(Float, nullable=False)
    reason = Column(SQLEnum(AdjustmentReason), nullable=False)
    notes = Column(String(255), nullable=True)
    
    product = relationship("Product")
    user = relationship("User")
