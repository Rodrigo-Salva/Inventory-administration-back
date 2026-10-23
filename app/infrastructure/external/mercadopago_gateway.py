"""Adaptador de Mercado Pago para el puerto PaymentGateway."""

import asyncio
import logging
from decimal import Decimal

import mercadopago

from app.application.billing.dto import CheckoutResult, PaymentInfo
from app.domain.billing.errors import PaymentGatewayError
from app.domain.billing.rules import tenant_reference
from app.infrastructure.config import settings

logger = logging.getLogger(__name__)

_PLACEHOLDER_TOKEN = "your_access_token"


class MercadoPagoGateway:
    def __init__(self):
        token = settings.mp_access_token
        self.sdk = mercadopago.SDK(token) if token and token != _PLACEHOLDER_TOKEN else None
        if not self.sdk:
            logger.warning("Mercado Pago sin credenciales válidas: el servicio de pagos está deshabilitado.")

    @staticmethod
    def _return_url() -> str:
        origins = settings.cors_origins if isinstance(settings.cors_origins, list) else []
        return next((o for o in origins if o != "*"), "http://localhost:3000")

    async def create_checkout(self, tenant_id: int, plan: str, price: Decimal) -> CheckoutResult:
        if not self.sdk:
            raise PaymentGatewayError("SDK no inicializado. Verifique sus credenciales.")
        base = self._return_url()
        preference = {
            "items": [{
                "title": f"Suscripción SaaS - Plan {plan}",
                "quantity": 1,
                "unit_price": float(price),
                "currency_id": settings.subscription_currency,
            }],
            "external_reference": tenant_reference(tenant_id),
            "metadata": {"plan": plan},
            "back_urls": {k: f"{base}/dashboard" for k in ("success", "failure", "pending")},
        }
        try:
            response = await asyncio.to_thread(self.sdk.preference().create, preference)
        except Exception as error:  # el SDK lanza excepciones de red heterogéneas
            logger.error("Error creando preferencia de Mercado Pago: %s", error)
            raise PaymentGatewayError("No se pudo conectar con Mercado Pago") from error
        body = response.get("response")
        if response.get("status") not in (200, 201):
            detail = body.get("message", "Error desconocido") if isinstance(body, dict) else str(body)
            logger.error("Mercado Pago rechazó la preferencia (%s): %s", response.get("status"), body)
            raise PaymentGatewayError(detail)
        return CheckoutResult(body.get("id"), body.get("init_point"), body.get("sandbox_init_point"))

    async def fetch_payment(self, payment_id: str) -> PaymentInfo | None:
        if not self.sdk:
            return None
        try:
            response = await asyncio.to_thread(self.sdk.payment().get, payment_id)
        except Exception as error:
            logger.error("Error consultando el pago %s: %s", payment_id, error)
            return None
        data = response.get("response") if response.get("status") == 200 else None
        if not isinstance(data, dict):
            return None
        return PaymentInfo(
            status=data.get("status", ""),
            external_reference=data.get("external_reference"),
            amount=Decimal(str(data.get("transaction_amount") or 0)),
            plan=(data.get("metadata") or {}).get("plan"),
        )
