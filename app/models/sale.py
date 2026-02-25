from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Text, Index
from sqlalchemy.orm import relationship
from .base import TimestampMixin, Base
import enum

class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    OTHER = "other"

class SaleStatus(str, enum.Enum):
    COMPLETED = "completed"
    ANNULLED = "annulled"

class Sale(Base, TimestampMixin):
    """Modelo de venta"""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    payment_method = Column(String(20), nullable=False, default=PaymentMethod.CASH)
    status = Column(String(20), nullable=False, default=SaleStatus.COMPLETED)
    notes = Column(Text, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    user = relationship("User")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Sale(id={self.id}, total={self.total_amount})>"

class SaleItem(Base):
    """Modelo de ítem de venta"""
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    # Relaciones
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")

    def __repr__(self):
        return f"<SaleItem(id={self.id}, product_id={self.product_id}, qty={self.quantity})>"
