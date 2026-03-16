import mercadopago
from typing import Dict, Any, Optional
from ..core.config import settings
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class PaymentService:
    def __init__(self):
        self.sdk = None
        if settings.mp_access_token and settings.mp_access_token != "your_access_token":
            try:
                self.sdk = mercadopago.SDK(settings.mp_access_token)
            # No print here to keep logs clean
            except Exception as e:
                logger.error(f"Error inicializando SDK de Mercado Pago: {str(e)}")
        else:
            logger.warning("Mercado Pago Access Token no configurado o es el placeholder. El servicio de pagos funcionará en modo limitado.")

    async def create_subscription_preference(self, tenant_id: int, plan_name: str, price: float) -> Dict[str, Any]:
        """Crea una preferencia de pago para una suscripción al SaaS"""
        if not self.sdk:
            return {"error": "Mercado Pago SDK no inicializado. Verifique sus credenciales."}

        # Intentar obtener base_url para redirecciones
        base_url = "http://localhost:3000"
        if settings.cors_origins and isinstance(settings.cors_origins, list) and len(settings.cors_origins) > 0:
            # Si el primero es *, buscar el siguiente o usar localhost
            for origin in settings.cors_origins:
                if origin != "*":
                    base_url = origin
                    break

        preference_data = {
            "items": [
                {
                    "title": f"Suscripción SaaS - Plan {plan_name}",
                    "quantity": 1,
                    "unit_price": float(price),
                    "currency_id": "PEN"
                }
            ],
            "external_reference": f"tenant_{tenant_id}",
            "back_urls": {
                "success": f"{base_url}/dashboard",
                "failure": f"{base_url}/dashboard",
                "pending": f"{base_url}/dashboard"
            },
            # "auto_return": "approved"
        }

        import json
        logger.info(f"PREFERENCE PAYLOAD: {json.dumps(preference_data)}")

        try:
            preference_response = self.sdk.preference().create(preference_data)
            status = preference_response.get("status")
            response = preference_response.get("response")
            
            if status not in [200, 201]:
                error_msg = response.get("message", "Error desconocido") if isinstance(response, dict) else str(response)
                logger.error(f"Error de API Mercado Pago (Status {status}): {response}")
                return {"error": error_msg, "status": status}
                
            return response
        except Exception as e:
            logger.error(f"Error creando preferencia de Mercado Pago: {str(e)}")
            return {"error": str(e)}

    async def process_webhook(self, data: Dict[str, Any], db_session_factory):
        """Procesa notificaciones de Mercado Pago (IPN/Webhooks)"""
        if not self.sdk:
            return False

        topic = data.get("type") or data.get("topic")
        resource_id = data.get("data", {}).get("id") or data.get("id")
        
        logger.info(f"Recibida notificación de Mercado Pago: {topic} ID: {resource_id}")
        
        if topic == "payment":
            try:
                # 1. Consultar el pago detallado
                payment_info = self.sdk.payment().get(resource_id)
                payment_data = payment_info["response"]
                
                status = payment_data.get("status")
                external_reference = payment_data.get("external_reference") # tenant_123
                
                if status == "approved" and external_reference and external_reference.startswith("tenant_"):
                    tenant_id = int(external_reference.replace("tenant_", ""))
                    
                    # 2. Actualizar el tenant
                    from ..repositories.tenant_repo import TenantRepository
                    from datetime import datetime, timedelta
                    
                    async with db_session_factory() as db:
                        repo = TenantRepository(db)
                        tenant = await repo.get_by_id(tenant_id)
                        if tenant:
                            tenant.plan = "premium" # O el plan que corresponda
                            tenant.is_active = True
                            # Renovar por 30 días
                            current_expiry = tenant.expires_at or datetime.now()
                            tenant.expires_at = current_expiry + timedelta(days=30)
                            
                            await db.commit()
                            logger.info(f"Suscripción renovada para tenant {tenant_id}")
                            return True
            except Exception as e:
                logger.error(f"Error procesando webhook de pago: {str(e)}")
                return False
        
        return True
