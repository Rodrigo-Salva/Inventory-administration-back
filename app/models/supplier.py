from sqlalchemy import Column, Integer, String, ForeignKey, Index, Text, Boolean
from sqlalchemy.orm import relationship
from .base import TimestampMixin, SoftDeleteMixin
from .base import Base


class Supplier(Base, TimestampMixin, SoftDeleteMixin):
    """Modelo de proveedores"""
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    
    # Información básica
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    tax_id = Column(String(50), nullable=True)  # RUC, NIT, etc.
    
    # Contacto
    contact_name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    mobile = Column(String(20), nullable=True)
    
    # Dirección
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Términos comerciales
    payment_terms = Column(String(100), nullable=True)  # ej: "30 días", "Contado"
    credit_limit = Column(Integer, nullable=True)
    
    # Estado
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Notas
    notes = Column(Text, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant", back_populates="suppliers")
    products = relationship("Product", back_populates="supplier")
    
    # Índices
    __table_args__ = (
        Index('idx_suppliers_tenant_active', 'tenant_id', 'is_active'),
        Index('idx_suppliers_tenant_name', 'tenant_id', 'name'),
    )
    
    def __repr__(self):
        return f"<Supplier(id={self.id}, code='{self.code}', name='{self.name}')>"
