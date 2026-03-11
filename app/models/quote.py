from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Text, Date
from sqlalchemy.orm import relationship
from .base import TimestampMixin, Base
import enum
import datetime

class QuoteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CONVERTED = "converted"

class Quote(Base, TimestampMixin):
    """Modelo de cotización / presupuesto"""
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Usuario que la crea
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True, nullable=True)
    
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(20), nullable=False, default=QuoteStatus.PENDING)
    valid_until = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Referencia a la venta si se convierte
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True, index=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    user = relationship("User")
    customer = relationship("Customer")
    sale = relationship("Sale")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")

    @property
    def is_expired(self) -> bool:
        return datetime.date.today() > self.valid_until

    def __repr__(self):
        return f"<Quote(id={self.id}, total={self.total_amount}, status={self.status})>"

class QuoteItem(Base):
    """Modelo de ítem de cotización"""
    __tablename__ = "quote_items"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    # Relaciones
    quote = relationship("Quote", back_populates="items")
    product = relationship("Product")

    def __repr__(self):
        return f"<QuoteItem(id={self.id}, product_id={self.product_id}, qty={self.quantity})>"
