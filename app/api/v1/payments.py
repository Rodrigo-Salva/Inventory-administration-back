from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ...models import get_db
from ...dependencies import get_current_tenant, require_role
from ...models.user import User, UserRole
from ...services.payment_service import PaymentService

router = APIRouter(tags=["Payments"])

@router.post("/checkout")
async def create_checkout(
    plan: str = Body(..., embed=True),
    price: float = Body(..., embed=True),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Crea una preferencia de pago en Mercado Pago"""
    service = PaymentService()
    preference = await service.create_subscription_preference(tenant_id, plan, price)
    
    if not preference or "error" in preference:
        error_detail = preference.get("error") if preference else "No se pudo conectar con Mercado Pago"
        raise HTTPException(
            status_code=400, 
            detail=f"Mercado Pago Error: {error_detail}"
        )
        
    return {
        "preference_id": preference.get("id"),
        "init_point": preference.get("init_point"),
        "sandbox_init_point": preference.get("sandbox_init_point")
    }

from ...models.base import async_session

@router.post("/webhook")
async def payment_webhook(
    request: Request
):
    """Recibe notificaciones de Mercado Pago"""
    data = await request.json()
    service = PaymentService()
    await service.process_webhook(data, async_session)
    
    return {"status": "ok"}
