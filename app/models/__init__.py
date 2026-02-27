from .base import Base, get_db, engine

# Importar todos los modelos para que Alembic los detecte
from .tenant import Tenant
from .user import User
from .product import Product
from .category import Category
from .supplier import Supplier
from .inventory_movement import InventoryMovement, MovementType
from .stock_alert import StockAlert, AlertType, AlertStatus
from .sale import Sale, SaleItem, PaymentMethod
from .audit_log import AuditLog
from .role import Role, Permission

__all__ = [
    "Base",
    "get_db",
    "engine",
    "Tenant",
    "User",
    "Product",
    "Category",
    "Supplier",
    "InventoryMovement",
    "MovementType",
    "StockAlert",
    "AlertType",
    "AlertStatus",
    "AuditLog",
    "Sale",
    "SaleItem",
    "PaymentMethod",
    "Role",
    "Permission",
]