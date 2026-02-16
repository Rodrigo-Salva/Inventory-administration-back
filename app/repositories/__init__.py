from .base_repository import BaseRepository
from .product_repo import ProductRepository
from .category_repo import CategoryRepository
from .supplier_repo import SupplierRepository
from .inventory_movement_repo import InventoryMovementRepository
from .stock_alert_repo import StockAlertRepository

# Mantener UserRepository si existe
try:
    from .user_repo import UserRepository
except ImportError:
    UserRepository = None

__all__ = [
    "BaseRepository",
    "ProductRepository",
    "CategoryRepository",
    "SupplierRepository",
    "InventoryMovementRepository",
    "StockAlertRepository",
    "UserRepository",
]