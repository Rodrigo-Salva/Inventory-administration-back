from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime, Index
from sqlalchemy.orm import relationship
from .base import TimestampMixin, Base
import enum
from datetime import datetime

class CreditStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    ANNULLED = "annulled"

class Credit(Base, TimestampMixin):
    """Modelo para manejar el crédito otorgado a un cliente por una venta"""
    __tablename__ = "credits"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True, nullable=False)
    sale_id = Column(Integer, ForeignKey("sales.id"), index=True, nullable=False)
    
    total_amount = Column(Numeric(12, 2), nullable=False)
    remaining_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False, default=CreditStatus.PENDING)
    due_date = Column(DateTime, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    customer = relationship("Customer")
    sale = relationship("Sale")
    payments = relationship("Payment", back_populates="credit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Credit(id={self.id}, customer_id={self.customer_id}, remaining={self.remaining_amount})>"
