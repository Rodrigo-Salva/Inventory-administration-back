from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Text, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
import enum
from .base import Base, TimestampMixin, SoftDeleteMixin

class PurchaseStatus(str, enum.Enum):
    DRAFT = "draft"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class PurchasePaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"

class Purchase(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "purchases"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), index=True, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Usuario que realizó la compra

    
    reference_number = Column(String(100), nullable=True)  # Factura del proveedor
    total_amount = Column(Numeric(12, 2), default=0, nullable=False)
    status = Column(SQLEnum(PurchaseStatus), default=PurchaseStatus.DRAFT, nullable=False)
    payment_status = Column(SQLEnum(PurchasePaymentStatus), default=PurchasePaymentStatus.PENDING, nullable=False)
    due_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    supplier = relationship("Supplier")
    branch = relationship("Branch")
    user = relationship("User")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Purchase(id={self.id}, supplier_id={self.supplier_id}, total={self.total_amount}, status='{self.status}')>"

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    
    # Relaciones
    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product")

    def __repr__(self):
        return f"<PurchaseItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"
