from sqlalchemy import Column, Integer, String, ForeignKey, Date, Boolean, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class ProductBatch(Base, TimestampMixin):
    """Modelo para control de lotes y fechas de vencimiento"""
    __tablename__ = "product_batches"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), index=True, nullable=False)
    
    batch_number = Column(String(100), nullable=False)
    expiration_date = Column(Date, nullable=False)
    
    # Cantidades
    initial_quantity = Column(Integer, nullable=False, default=0)
    current_quantity = Column(Integer, nullable=False, default=0)
    
    # Estado del lote
    is_active = Column(Boolean, default=True, nullable=False)

    # Relaciones
    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="batches")

    # Índices para búsquedas frecuentes
    __table_args__ = (
        Index('idx_batches_product_expiration', 'product_id', 'expiration_date'),
        Index('idx_batches_tenant_active', 'tenant_id', 'is_active'),
    )

    def __repr__(self):
        return f"<ProductBatch(id={self.id}, product_id={self.product_id}, batch='{self.batch_number}', qty={self.current_quantity})>"
