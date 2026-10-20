from .base_repository import BaseRepository
from app.modules.catalog.infrastructure.persistence.repositories.product_repo import ProductRepository
from app.modules.catalog.infrastructure.persistence.repositories.category_repo import CategoryRepository
from app.modules.catalog.infrastructure.persistence.repositories.supplier_repo import SupplierRepository
from app.modules.inventory.infrastructure.persistence.repositories.inventory_movement_repo import InventoryMovementRepository
from .stock_alert_repo import StockAlertRepository
from app.modules.identity.infrastructure.persistence.repositories.tenant_repo import TenantRepository
from .customer_repo import CustomerRepository
from app.modules.purchasing.infrastructure.persistence.repositories.purchase_repo import PurchaseRepository
from .sale_repo import SaleRepository
from .quote_repo import QuoteRepository
from .credit_repo import CreditRepository
from .payment_repo import PaymentRepository

from app.modules.identity.infrastructure.persistence.repositories.user_repo import UserRepository

__all__ = [
    "BaseRepository",
    "ProductRepository",
    "CategoryRepository",
    "SupplierRepository",
    "InventoryMovementRepository",
    "StockAlertRepository",
    "UserRepository",
    "TenantRepository",
    "CustomerRepository",
    "PurchaseRepository",
    "SaleRepository",
    "QuoteRepository",
    "CreditRepository",
    "PaymentRepository",
]
