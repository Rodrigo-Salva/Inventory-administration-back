from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.billing.dto import TenantSubscription
from app.infrastructure.persistence.models.identity.processed_payment import ProcessedPayment
from app.infrastructure.persistence.models.identity.tenant import Tenant


class SqlAlchemySubscriptionStore:
    """Adaptador SQLAlchemy del puerto SubscriptionStore."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_payment_once(self, payment_id: str, tenant_id: int) -> bool:
        result = await self.db.execute(
            pg_insert(ProcessedPayment)
            .values(payment_id=payment_id, tenant_id=tenant_id)
            .on_conflict_do_nothing(index_elements=["payment_id"])
            .returning(ProcessedPayment.payment_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_subscription(self, tenant_id: int) -> TenantSubscription | None:
        tenant = await self.db.get(Tenant, tenant_id, with_for_update=True)
        return TenantSubscription(tenant.id, tenant.expires_at) if tenant else None

    async def renew(self, tenant_id: int, plan: str, expires_at: datetime) -> None:
        tenant = await self.db.get(Tenant, tenant_id)
        tenant.plan = plan
        tenant.expires_at = expires_at
        await self.db.flush()
