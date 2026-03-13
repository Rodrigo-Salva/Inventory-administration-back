from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum
from datetime import datetime

class CashSessionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class CashSession(Base, TimestampMixin):
    """Modelo para sesiones de caja (turnos)"""
    __tablename__ = "cash_sessions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    
    status = Column(String(20), nullable=False, default=CashSessionStatus.OPEN)
    
    # Balances
    opening_balance = Column(Numeric(12, 2), nullable=False, default=0)
    expected_balance = Column(Numeric(12, 2), nullable=True) # Calculado al cerrar
    closing_balance = Column(Numeric(12, 2), nullable=True)  # Lo que el usuario dice que hay
    
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    
    notes = Column(String(255), nullable=True)

    # Relaciones
    tenant = relationship("Tenant")
    user = relationship("User")
    sales = relationship("Sale", back_populates="cash_session")

    def __repr__(self):
        return f"<CashSession(id={self.id}, user_id={self.user_id}, status={self.status})>"
