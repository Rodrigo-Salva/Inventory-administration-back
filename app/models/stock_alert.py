from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Index, Boolean
from sqlalchemy.orm import relationship
from .base import TimestampMixin
from .base import Base
import enum


class AlertType(str, enum.Enum):
    """Tipos de alertas de stock"""
    LOW_STOCK = "low_stock"  # Stock bajo
    OUT_OF_STOCK = "out_of_stock"  # Sin stock
    OVERSTOCK = "overstock"  # Sobrestock
    EXPIRING_SOON = "expiring_soon"  # Próximo a vencer (para futuras features)


class AlertStatus(str, enum.Enum):
    """Estados de las alertas"""
    ACTIVE = "active"  # Alerta activa
    RESOLVED = "resolved"  # Alerta resuelta
    DISMISSED = "dismissed"  # Alerta descartada


class StockAlert(Base, TimestampMixin):
    """Modelo de alertas de stock"""
    __tablename__ = "stock_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), index=True, nullable=False)
    
    # Tipo y estado de alerta
    alert_type = Column(Enum(AlertType, native_enum=False, length=50), nullable=False, index=True)
    status = Column(Enum(AlertStatus, native_enum=False, length=50), default=AlertStatus.ACTIVE, nullable=False, index=True)
    
    # Información de la alerta
    current_stock = Column(Integer, nullable=False)
    threshold_value = Column(Integer, nullable=True)  # Valor del umbral que disparó la alerta
    
    # Mensaje personalizado
    message = Column(String(500), nullable=True)
    
    # Notificación
    is_notified = Column(Boolean, default=False, nullable=False)  # Si ya se notificó al usuario
    
    # Relaciones
    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="alerts")
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_tenant_status', 'tenant_id', 'status'),
        Index('idx_tenant_type', 'tenant_id', 'alert_type'),
        Index('idx_product_status', 'product_id', 'status'),
        Index('idx_tenant_active', 'tenant_id', 'status', 'is_notified'),
    )
    
    def resolve(self):
        """Marca la alerta como resuelta"""
        self.status = AlertStatus.RESOLVED
    
    def dismiss(self):
        """Descarta la alerta"""
        self.status = AlertStatus.DISMISSED
    
    @property
    def is_active(self) -> bool:
        """Verifica si la alerta está activa"""
        return self.status == AlertStatus.ACTIVE
    
    def __repr__(self):
        return f"<StockAlert(id={self.id}, product_id={self.product_id}, type={self.alert_type}, status={self.status})>"
