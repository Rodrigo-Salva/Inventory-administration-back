from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum
from datetime import datetime

class AuditStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class InventoryAudit(Base, TimestampMixin):
    """Encabezado de una sesión de Auditoría (Toma Física)"""
    __tablename__ = "inventory_audits"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(String(20), default=AuditStatus.IN_PROGRESS, nullable=False)
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    branch = relationship("Branch")
    user = relationship("User")
    items = relationship("InventoryAuditItem", back_populates="audit", cascade="all, delete-orphan")

class InventoryAuditItem(Base, TimestampMixin):
    """Detalle de conteo por producto en una auditoría"""
    __tablename__ = "inventory_audit_items"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("inventory_audits.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    expected_stock = Column(Integer, nullable=False) # Lo que decía el sistema al iniciar
    counted_stock = Column(Integer, nullable=False)  # Lo que el usuario contó físically
    difference = Column(Integer, nullable=False)     # counted - expected
    
    is_adjusted = Column(Boolean, default=False)     # Si ya se aplicó el ajuste al inventario real
    notes = Column(Text, nullable=True)

    # Relaciones
    audit = relationship("InventoryAudit", back_populates="items")
    product = relationship("Product")
