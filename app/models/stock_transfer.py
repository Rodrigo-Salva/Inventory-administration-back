from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class StockTransferStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class StockTransfer(Base, TimestampMixin):
    """Modelo principal de traslados entre sucursales"""
    __tablename__ = "stock_transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    from_branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    to_branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(Enum(StockTransferStatus, native_enum=False, length=20), default=StockTransferStatus.PENDING, index=True)
    notes = Column(Text, nullable=True)
    reference = Column(String(100), nullable=True) # Código de referencia o guía
    
    # Metadatos del estado
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    from_branch = relationship("Branch", foreign_keys=[from_branch_id])
    to_branch = relationship("Branch", foreign_keys=[to_branch_id])
    user = relationship("User")
    items = relationship("StockTransferItem", back_populates="transfer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StockTransfer(id={self.id}, from={self.from_branch_id}, to={self.to_branch_id}, status={self.status})>"

class StockTransferItem(Base):
    """Items específicos dentro de un traslado"""
    __tablename__ = "stock_transfer_items"
    
    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(Integer, ForeignKey("stock_transfers.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=True)
    
    quantity = Column(Integer, nullable=False)
    
    # Relaciones
    transfer = relationship("StockTransfer", back_populates="items")
    product = relationship("Product")
    batch = relationship("ProductBatch")

    def __repr__(self):
        return f"<StockTransferItem(id={self.id}, product_id={self.product_id}, qty={self.quantity})>"
