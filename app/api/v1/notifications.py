from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ...dependencies import get_db_session, get_current_user
from ...repositories.stock_alert_repo import StockAlertRepository
from ...models.user import User

router = APIRouter()

@router.get("/")
async def get_notifications(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Obtiene alertas de stock no notificadas para el tenant"""
    repo = StockAlertRepository(db)
    alerts = await repo.get_unnotified_alerts(current_user.tenant_id)
    
    return [
        {
            "id": alert.id,
            "product_id": alert.product_id,
            "product_name": alert.product.name if alert.product else "Producto Desconocido",
            "alert_type": alert.alert_type,
            "message": alert.message,
            "current_stock": alert.current_stock,
            "threshold": alert.threshold_value,
            "created_at": alert.created_at
        }
        for alert in alerts
    ]

@router.post("/mark-read")
async def mark_notifications_read(
    alert_ids: List[int],
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Marca una lista de alertas como notificadas"""
    repo = StockAlertRepository(db)
    await repo.mark_as_notified(alert_ids)
    await db.commit()
    return {"status": "success"}

@router.get("/active")
async def get_active_notifications(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todas las alertas activas (vistas y no vistas)"""
    repo = StockAlertRepository(db)
    alerts = await repo.get_active_alerts(current_user.tenant_id)
    
    return [
        {
            "id": alert.id,
            "product_id": alert.product_id,
            "product_name": alert.product.name if alert.product else "Producto Desconocido",
            "alert_type": alert.alert_type,
            "message": alert.message,
            "current_stock": alert.current_stock,
            "threshold": alert.threshold,
            "is_notified": alert.is_notified,
            "created_at": alert.created_at
        }
        for alert in alerts
    ]
