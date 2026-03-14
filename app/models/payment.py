from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import relationship
from .base import TimestampMixin, Base
from .sale import PaymentMethod

class Payment(Base, TimestampMixin):
    """Modelo para registrar abonos a créditos de clientes"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    credit_id = Column(Integer, ForeignKey("credits.id"), index=True, nullable=False)
    
    amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(20), nullable=False, default=PaymentMethod.CASH)
    notes = Column(Text, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    credit = relationship("Credit", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, credit_id={self.credit_id}, amount={self.amount})>"
