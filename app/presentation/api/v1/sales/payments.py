import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.billing.dto import CreateCheckoutCommand, PaymentNotification
from app.application.billing.use_cases import ActivateSubscription, CreateCheckout
from app.domain.billing.rules import valid_webhook_signature
from app.infrastructure.config import settings
from app.infrastructure.config_plans import SettingsPlanCatalog
from app.infrastructure.external.mercadopago_gateway import MercadoPagoGateway
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User, UserRole
from app.infrastructure.persistence.repositories.identity.subscription_store import SqlAlchemySubscriptionStore
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.presentation.dependencies import get_current_tenant, require_role

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Payments"])


@router.post("/checkout")
async def create_checkout(
    plan: str = Body(..., embed=True, min_length=1, max_length=50),
    price: Optional[Decimal] = Body(None, embed=True, gt=0),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
):
    """Crea una preferencia de pago en Mercado Pago (el precio lo define el servidor)"""
    result = await CreateCheckout(MercadoPagoGateway(), SettingsPlanCatalog()).execute(
        CreateCheckoutCommand(tenant_id=tenant_id, plan=plan, client_price=price)
    )
    return {
        "preference_id": result.preference_id,
        "init_point": result.init_point,
        "sandbox_init_point": result.sandbox_init_point,
    }


@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Recibe notificaciones de Mercado Pago (firmadas e idempotentes)"""
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="Cuerpo inválido")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Cuerpo inválido")

    payment_id = (body.get("data") or {}).get("id") or body.get("id")
    payment_id = str(payment_id) if payment_id else None

    if settings.mp_webhook_secret:
        data_id = request.query_params.get("data.id") or payment_id
        if not valid_webhook_signature(
            settings.mp_webhook_secret,
            request.headers.get("x-signature"),
            request.headers.get("x-request-id"),
            data_id,
        ):
            raise HTTPException(status_code=401, detail="Firma inválida")
    else:
        logger.warning("MP_WEBHOOK_SECRET no configurado: el webhook solo se valida consultando a Mercado Pago")

    use_case = ActivateSubscription(
        MercadoPagoGateway(), SettingsPlanCatalog(), SqlAlchemySubscriptionStore(db), SqlAlchemyUnitOfWork(db)
    )
    await use_case.execute(PaymentNotification(topic=body.get("type") or body.get("topic"), payment_id=payment_id))
    return {"status": "ok"}
