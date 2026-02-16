from sqlalchemy import Column, Integer, String, ForeignKey, Index, Text, JSON
from sqlalchemy.orm import relationship
from .base import TimestampMixin
from .base import Base


class AuditLog(Base, TimestampMixin):
    """Modelo de auditoría para rastrear cambios en el sistema"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Información de la acción
    action = Column(String(50), nullable=False, index=True)  # CREATE, UPDATE, DELETE, etc.
    entity_type = Column(String(50), nullable=False, index=True)  # Product, Category, etc.
    entity_id = Column(Integer, nullable=False, index=True)
    
    # Cambios realizados
    old_values = Column(JSON, nullable=True)  # Valores anteriores
    new_values = Column(JSON, nullable=True)  # Valores nuevos
    
    # Metadata adicional
    ip_address = Column(String(45), nullable=True)  # IPv4 o IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Descripción legible
    description = Column(Text, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    user = relationship("User")
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_tenant_entity', 'tenant_id', 'entity_type', 'entity_id'),
        Index('idx_tenant_action', 'tenant_id', 'action'),
        Index('idx_tenant_date', 'tenant_id', 'created_at'),
        Index('idx_entity_date', 'entity_type', 'entity_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, entity={self.entity_type}:{self.entity_id})>"
