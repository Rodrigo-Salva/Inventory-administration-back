from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.infrastructure.persistence.database import Base, TimestampMixin

class LoyaltyConfig(Base, TimestampMixin):
    """Configuración del programa de lealtad por tenant"""
    __tablename__ = "loyalty_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, unique=True, nullable=False)
    
    # Configuración de acumulación
    points_per_amount = Column(Numeric(12, 2), default=1.00)  # Cantidad de dinero por cada punto generada
    amount_per_point = Column(Numeric(12, 2), default=1.00)   # Cuánto dinero vale un punto (puntos generados)
    
    # Ej: 1 punto por cada $100 gastados
    # Ej: 1 punto vale $10 de descuento
    
    is_active = Column(Boolean, default=True)
    min_redemption_points = Column(Integer, default=0) # Mínimo de puntos para poder canjear
    
    # Relaciones
    tenant = relationship("Tenant")

class LoyaltyTransaction(Base, TimestampMixin):
    """Historial de puntos (acumulación y redención)"""
    __tablename__ = "loyalty_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True, nullable=False)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True) # Asociado a una venta
    
    points = Column(Integer, nullable=False) # Positivo para acumulación, negativo para redención
    description = Column(String(255), nullable=True)
    transaction_type = Column(String(20), nullable=False) # earn, redeem, adjust
    
    # Relaciones
    customer = relationship("Customer")
    sale = relationship("Sale")
