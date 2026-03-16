import httpx
import json
import hmac
import hashlib
from typing import List, Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.webhook_repo import WebhookRepository
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class WebhookService:
    def __init__(self, db: AsyncSession):
        self.repo = WebhookRepository(db)

    async def register_webhook(self, tenant_id: int, url: str, events: List[str], description: Optional[str] = None):
        secret_key = hashlib.sha256(os.urandom(32)).hexdigest()
        return await self.repo.create(tenant_id, url, events, description, secret_key)

    async def send_to_webhook(self, webhook, event_name: str, payload: Dict[str, Any]):
        """Envía un evento a un webhook específico"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Preparar data
                data = {
                    "event": event_name,
                    "tenant_id": webhook.tenant_id,
                    "data": payload
                }
                body = json.dumps(data)
                
                # Firmar si hay secret_key
                headers = {"Content-Type": "application/json"}
                if webhook.secret_key:
                    signature = hmac.new(
                        webhook.secret_key.encode(),
                        body.encode(),
                        hashlib.sha256
                    ).hexdigest()
                    headers["X-Webhook-Signature"] = signature

                # Enviar
                response = await client.post(webhook.url, content=body, headers=headers)
                logger.info(f"Webhook enviado a {webhook.url}: Status {response.status_code}")
                return response.status_code
            except Exception as e:
                logger.error(f"Error enviando webhook a {webhook.url}: {str(e)}")
                return None

    async def dispatch_event(self, tenant_id: int, event_name: str, payload: Dict[str, Any]):
        """Despacha un evento a todos los webhooks suscritos de un tenant"""
        webhooks = await self.repo.get_by_event(tenant_id, event_name)
        
        if not webhooks:
            return

        for webhook in webhooks:
            await self.send_to_webhook(webhook, event_name, payload)

    @staticmethod
    async def trigger_webhook_task(tenant_id: int, event_name: str, payload: Dict[str, Any], db_factory):
        """Función estática para ser llamada por BackgroundTasks para despacho general"""
        async with db_factory() as db:
            service = WebhookService(db)
            await service.dispatch_event(tenant_id, event_name, payload)

    @staticmethod
    async def trigger_test_webhook_task(webhook_id: int, payload: Dict[str, Any], db_factory):
        """Función para probar un webhook específico independientemente de sus eventos"""
        from ..models.webhook import Webhook
        async with db_factory() as db:
            webhook = await db.get(Webhook, webhook_id)
            if webhook:
                service = WebhookService(db)
                await service.send_to_webhook(webhook, "webhook.test", payload)
