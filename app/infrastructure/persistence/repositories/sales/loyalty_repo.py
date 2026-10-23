from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.infrastructure.persistence.repositories.base_repository import BaseRepository
from app.infrastructure.persistence.models.sales.loyalty import LoyaltyConfig, LoyaltyTransaction

class LoyaltyRepository(BaseRepository[LoyaltyConfig]):
    def __init__(self, db: AsyncSession):
        super().__init__(LoyaltyConfig, db)

    async def get_config(self, tenant_id: int) -> LoyaltyConfig:
        """Obtiene la configuración de lealtad del tenant, la crea si no existe"""
        query = select(LoyaltyConfig).where(LoyaltyConfig.tenant_id == tenant_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()
        
        if not config:
            config = LoyaltyConfig(tenant_id=tenant_id)
            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)
            
        return config

    async def get_customer_transactions(self, tenant_id: int, customer_id: int) -> List[LoyaltyTransaction]:
        query = select(LoyaltyTransaction).where(
            LoyaltyTransaction.tenant_id == tenant_id,
            LoyaltyTransaction.customer_id == customer_id
        ).order_by(LoyaltyTransaction.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_transaction(self, transaction_id: int, tenant_id: int) -> Optional[LoyaltyTransaction]:
        result = await self.db.execute(
            select(LoyaltyTransaction).where(
                LoyaltyTransaction.id == transaction_id, LoyaltyTransaction.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
