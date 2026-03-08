from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False) # e.g., Rent, Salaries, Marketing, Utilities
    description = Column(Text, nullable=True)
    date = Column(Date, nullable=False)
    reference = Column(String(100), nullable=True) # e.g., Invoice number
    
    # Relationships
    tenant = relationship("Tenant", back_populates="expenses")
