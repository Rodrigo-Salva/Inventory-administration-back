from sqlalchemy import Column, Integer, String, ForeignKey, Index, Text, Boolean
from sqlalchemy.orm import relationship
from .base import TimestampMixin, SoftDeleteMixin
from .base import Base


class Customer(Base, TimestampMixin, SoftDeleteMixin):
    """Modelo de clientes"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    
    # Información básica
    name = Column(String(200), nullable=False, index=True)
    document_type = Column(String(50), nullable=True) # ej: DNI, RUC, NIT
    document_number = Column(String(50), index=True, nullable=True)
    
    # Contacto
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Dirección
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Estado
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Notas
    notes = Column(Text, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    
    # Índices
    __table_args__ = (
        Index('idx_customers_tenant_active', 'tenant_id', 'is_active'),
        Index('idx_customers_tenant_name', 'tenant_id', 'name'),
    )
    
    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}')>"
