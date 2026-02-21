from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import TimestampMixin, SoftDeleteMixin
from .base import Base


class Category(Base, TimestampMixin, SoftDeleteMixin):
    """Modelo de categorías jerárquicas para productos"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(50), nullable=True, unique=True, index=True)
    description = Column(String(500), nullable=True)
    
    # Orden de visualización
    display_order = Column(Integer, default=0)
    
    # Relaciones
    tenant = relationship("Tenant", back_populates="categories")
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="category")
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_categories_tenant_parent', 'tenant_id', 'parent_id'),
        Index('idx_categories_tenant_name', 'tenant_id', 'name'),
    )
    
    @property
    def full_path(self) -> str:
        """Retorna la ruta completa de la categoría (ej: 'Electrónica > Computadoras > Laptops')"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name
    
    @property
    def level(self) -> int:
        """Retorna el nivel de profundidad de la categoría"""
        if self.parent:
            return self.parent.level + 1
        return 0
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', parent_id={self.parent_id})>"
