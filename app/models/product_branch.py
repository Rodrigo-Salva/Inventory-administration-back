from sqlalchemy import Column, Integer, ForeignKey, Index, Numeric
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class ProductBranch(Base, TimestampMixin):
    """
    Tabla intermedia para manejar el stock por sucursal.
    Un producto puede tener distinto stock en distintas sucursales.
    """
    __tablename__ = "product_branches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    
    # Inventario Específico de Sucursal
    stock = Column(Integer, default=0, nullable=False)
    min_stock = Column(Integer, default=10, nullable=False)
    max_stock = Column(Integer, nullable=True)
    
    # Precio variable por sucursal (opcional)
    price = Column(Numeric(10, 2), nullable=True) # Si es nulo, usa el principal

    product = relationship("Product", back_populates="branch_stocks")
    branch = relationship("Branch")

    __table_args__ = (
        Index('idx_product_branch', 'product_id', 'branch_id', unique=True),
    )
