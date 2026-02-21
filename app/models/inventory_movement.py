from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Index, Text, Numeric
from sqlalchemy.orm import relationship
from .base import TimestampMixin
from .base import Base
import enum


class MovementType(str, enum.Enum):
    """Tipos de movimiento de inventario"""
    ENTRY = "entry"  # Entrada (compra, devolución de cliente)
    EXIT = "exit"  # Salida (venta, devolución a proveedor)
    ADJUSTMENT = "adjustment"  # Ajuste de inventario
    TRANSFER = "transfer"  # Transferencia entre ubicaciones
    INITIAL = "initial"  # Inventario inicial


class InventoryMovement(Base, TimestampMixin):
    """Modelo de movimientos de inventario"""
    __tablename__ = "inventory_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Usuario que realizó el movimiento
    
    # Tipo y cantidad
    movement_type = Column(Enum(MovementType, native_enum=False, length=20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)  # Positivo para entradas, negativo para salidas
    
    # Stock antes y después del movimiento
    stock_before = Column(Integer, nullable=False)
    stock_after = Column(Integer, nullable=False)
    
    # Costo unitario (para valorización de inventario)
    unit_cost = Column(Numeric(10, 2), nullable=True)
    
    # Referencia externa (número de factura, orden de compra, etc.)
    reference = Column(String(100), nullable=True, index=True)
    
    # Notas
    notes = Column(Text, nullable=True)
    
    # Relaciones
    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="movements")
    user = relationship("User")
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_movements_tenant_product', 'tenant_id', 'product_id'),
        Index('idx_movements_tenant_type', 'tenant_id', 'movement_type'),
        Index('idx_movements_tenant_date', 'tenant_id', 'created_at'),
        Index('idx_movements_product_date', 'product_id', 'created_at'),
    )
    
    @property
    def is_entry(self) -> bool:
        """Verifica si es un movimiento de entrada"""
        return self.movement_type in [MovementType.ENTRY, MovementType.INITIAL]
    
    @property
    def is_exit(self) -> bool:
        """Verifica si es un movimiento de salida"""
        return self.movement_type == MovementType.EXIT
    
    @property
    def total_value(self) -> float:
        """Calcula el valor total del movimiento"""
        if self.unit_cost:
            return abs(self.quantity) * float(self.unit_cost)
        return 0.0
    
    def __repr__(self):
        return f"<InventoryMovement(id={self.id}, product_id={self.product_id}, type={self.movement_type}, qty={self.quantity})>"
