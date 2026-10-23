from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inventory.alerts import ActiveAlert, StockAlerts, StockLevel
from app.infrastructure.external.notification_service import NotificationService
from app.infrastructure.persistence.models.catalog.product import Product
from app.infrastructure.persistence.models.identity.tenant import Tenant
from app.infrastructure.persistence.models.inventory.stock_alert import AlertStatus, AlertType, StockAlert


class SqlAlchemyAlertStore:
    """Adaptador SQLAlchemy del puerto AlertStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def active_alerts(self, tenant_id: int, product_id: int) -> list[ActiveAlert]:
        result = await self.db.execute(
            select(StockAlert).where(
                StockAlert.product_id == product_id,
                StockAlert.tenant_id == tenant_id,
                StockAlert.status == AlertStatus.ACTIVE,
            )
        )
        return [
            ActiveAlert(a.id, str(getattr(a.alert_type, "value", a.alert_type))) for a in result.scalars().all()
        ]

    async def open_alert(
        self, tenant_id: int, product_id: int, alert_type: str, stock: int, threshold: int, message: str
    ) -> None:
        self.db.add(
            StockAlert(
                tenant_id=tenant_id,
                product_id=product_id,
                alert_type=AlertType(alert_type),
                status=AlertStatus.ACTIVE,
                current_stock=stock,
                threshold_value=threshold,
                message=message,
            )
        )
        await self.db.flush()

    async def resolve(self, alert_id: int) -> None:
        alert = await self.db.get(StockAlert, alert_id)
        alert.resolve()
        await self.db.flush()


class SqlAlchemyTenantContacts:
    """Adaptador SQLAlchemy del puerto TenantContacts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def alert_email(self, tenant_id: int) -> str | None:
        return (await self.db.execute(select(Tenant.email).where(Tenant.id == tenant_id))).scalar_one_or_none()


def build_stock_alerts(db: AsyncSession) -> StockAlerts:
    return StockAlerts(SqlAlchemyAlertStore(db), SqlAlchemyTenantContacts(db), NotificationService())


def level_of(product: Product) -> StockLevel:
    return StockLevel(product.id, product.name, product.stock, product.min_stock)
