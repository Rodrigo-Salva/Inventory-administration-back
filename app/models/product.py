from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin


class Product(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    
    # Información básica
    name = Column(String(200), nullable=False, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    barcode = Column(String(100), unique=True, nullable=True, index=True)
    description = Column(Text, nullable=True)
    
    # Precios y costos
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=True)  # Costo de adquisición
    
    # Inventario
    stock = Column(Integer, default=0, nullable=False)
    min_stock = Column(Integer, default=10, nullable=False)
    max_stock = Column(Integer, nullable=True)  # Para alertas de sobrestock
    
    # Características físicas
    weight = Column(Float, nullable=True)  # en kg
    dimensions = Column(String(50), nullable=True)  # ej: "10x20x30 cm"
    
    # Estado
    is_active = Column(Boolean, default=True, nullable=False)  # Producto activo para venta
    
    # Relaciones
    tenant = relationship("Tenant", back_populates="products")
    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    movements = relationship("InventoryMovement", back_populates="product", cascade="all, delete-orphan")
    alerts = relationship("StockAlert", back_populates="product", cascade="all, delete-orphan")
    
    # Índices compuestos para optimización
    __table_args__ = (
        Index('idx_tenant_category', 'tenant_id', 'category_id'),
        Index('idx_tenant_active', 'tenant_id', 'is_active'),
        Index('idx_tenant_stock', 'tenant_id', 'stock'),
    )
    
    @property
    def is_low_stock(self) -> bool:
        """Verifica si el producto tiene stock bajo"""
        return self.stock <= self.min_stock
    
    @property
    def is_out_of_stock(self) -> bool:
        """Verifica si el producto está sin stock"""
        return self.stock <= 0
    
    @property
    def stock_percentage(self) -> float:
        """Calcula el porcentaje de stock actual vs stock mínimo"""
        if self.min_stock == 0:
            return 100.0
        return (self.stock / self.min_stock) * 100
    
    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}', stock={self.stock})>"