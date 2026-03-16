from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Webhook(Base, TimestampMixin):
    """Modelo para suscripciones a webhooks por tenant"""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    
    url = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    secret_key = Column(String(100), nullable=True) # Para firmar peticiones
    
    is_active = Column(Boolean, default=True)
    
    # Eventos suscritos: ['sale.created', 'product.stock_low', etc.]
    events = Column(JSON, nullable=False, default=[])
    
    # Relaciones
    tenant = relationship("Tenant")

    def __repr__(self):
        return f"<Webhook(id={self.id}, url={self.url}, tenant_id={self.tenant_id})>"
