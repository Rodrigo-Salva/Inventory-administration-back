from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from .base_repository import BaseRepository
from ..models.loyalty import LoyaltyConfig, LoyaltyTransaction
from ..models.customer import Customer
from ..schemas.loyalty import LoyaltyConfigUpdate, LoyaltyTransactionCreate

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

    async def update_config(self, tenant_id: int, update_data: LoyaltyConfigUpdate) -> LoyaltyConfig:
        config = await self.get_config(tenant_id)
        
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
            
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

    async def add_transaction(self, tenant_id: int, trans_data: LoyaltyTransactionCreate) -> LoyaltyTransaction:
        # 1. Crear transacción
        transaction = LoyaltyTransaction(
            tenant_id=tenant_id,
            **trans_data.model_dump()
        )
        self.db.add(transaction)
        
        # 2. Actualizar puntos del cliente
        query = select(Customer).where(Customer.id == trans_data.customer_id)
        result = await self.db.execute(query)
        customer = result.scalar_one_or_none()
        
        if customer:
            customer.loyalty_points += trans_data.points
            
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction
