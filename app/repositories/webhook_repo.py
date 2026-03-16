from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from ..models.webhook import Webhook

class WebhookRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: int, url: str, events: List[str], description: Optional[str] = None, secret_key: Optional[str] = None) -> Webhook:
        webhook = Webhook(
            tenant_id=tenant_id,
            url=url,
            events=events,
            description=description,
            secret_key=secret_key
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def get_by_tenant(self, tenant_id: int) -> List[Webhook]:
        result = await self.db.execute(
            select(Webhook).where(Webhook.tenant_id == tenant_id, Webhook.is_active == True)
        )
        return list(result.scalars().all())

    async def get_by_event(self, tenant_id: int, event_name: str) -> List[Webhook]:
        """Obtiene webhooks de un tenant suscritos a un evento específico"""
        # Nota: PostgreSQL JSONB soportaría mejor esta consulta con @>, 
        # pero para compatibilidad usaremos una carga y filtrado o una consulta genérica de JSON
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.tenant_id == tenant_id,
                Webhook.is_active == True
            )
        )
        all_webhooks = result.scalars().all()
        return [w for w in all_webhooks if event_name in w.events]

    async def delete(self, webhook_id: int, tenant_id: int) -> bool:
        result = await self.db.execute(
            delete(Webhook).where(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id)
        )
        await self.db.commit()
        return result.rowcount > 0
