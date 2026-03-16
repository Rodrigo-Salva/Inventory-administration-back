from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks
from ..models import Product, StockAlert, AlertType, AlertStatus
from ..repositories import StockAlertRepository, TenantRepository
from .notification_service import NotificationService
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class StockAlertService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.alert_repo = StockAlertRepository(db)
        self.tenant_repo = TenantRepository(db)
        self.notif_service = NotificationService()

    async def check_and_trigger_alerts(self, product: Product, tenant_id: int, background_tasks: Optional[BackgroundTasks] = None):
        """Verifica el stock de un producto y dispara alertas si es necesario"""
        
        # Obtener alertas activas para este producto
        from sqlalchemy import select, and_
        query = select(StockAlert).where(
            and_(
                StockAlert.product_id == product.id,
                StockAlert.tenant_id == tenant_id,
                StockAlert.status == AlertStatus.ACTIVE
            )
        )
        result = await self.db.execute(query)
        active_alerts = result.scalars().all()
        
        should_notify = False
        alert_msg = ""
        
        # 1. Sin Stock
        if product.stock <= 0:
            has_out_alert = any(a.alert_type == AlertType.OUT_OF_STOCK for a in active_alerts)
            if not has_out_alert:
                alert_msg = f"Producto '{product.name}' sin stock"
                await self.alert_repo.create({
                    "tenant_id": tenant_id,
                    "product_id": product.id,
                    "alert_type": AlertType.OUT_OF_STOCK,
                    "status": AlertStatus.ACTIVE,
                    "current_stock": product.stock,
                    "threshold_value": 0,
                    "message": alert_msg
                })
                should_notify = True
                
        # 2. Stock Bajo
        elif product.stock <= product.min_stock:
            has_low_alert = any(a.alert_type == AlertType.LOW_STOCK for a in active_alerts)
            if not has_low_alert:
                alert_msg = f"Stock bajo para '{product.name}': {product.stock} unidades (mínimo: {product.min_stock})"
                await self.alert_repo.create({
                    "tenant_id": tenant_id,
                    "product_id": product.id,
                    "alert_type": AlertType.LOW_STOCK,
                    "status": AlertStatus.ACTIVE,
                    "current_stock": product.stock,
                    "threshold_value": product.min_stock,
                    "message": alert_msg
                })
                should_notify = True

        # 3. Notificar via Email
        if should_notify and background_tasks:
            tenant = await self.tenant_repo.get_by_id(tenant_id)
            if tenant and tenant.email:
                body = self.notif_service.get_stock_alert_template(
                    product.name,
                    product.stock,
                    product.min_stock if product.stock > 0 else 0
                )
                background_tasks.add_task(
                    self.notif_service.send_email,
                    tenant.email,
                    f"⚠️ Alerta de Inventario: {product.name}",
                    body
                )
                logger.info(f"Tarea de notificación de stock encolada para {tenant.email}")

    async def resolve_alerts_if_needed(self, product: Product, tenant_id: int):
        """Resuelve alertas si el stock ha mejorado"""
        from sqlalchemy import select, and_
        query = select(StockAlert).where(
            and_(
                StockAlert.product_id == product.id,
                StockAlert.tenant_id == tenant_id,
                StockAlert.status == AlertStatus.ACTIVE
            )
        )
        result = await self.db.execute(query)
        active_alerts = result.scalars().all()
        
        for alert in active_alerts:
            if alert.alert_type == AlertType.OUT_OF_STOCK and product.stock > 0:
                alert.resolve()
            elif alert.alert_type == AlertType.LOW_STOCK and product.stock > product.min_stock:
                alert.resolve()
                
        await self.db.flush()
