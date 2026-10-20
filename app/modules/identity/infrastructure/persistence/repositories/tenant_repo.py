from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.modules.identity.infrastructure.persistence.models import Tenant
from app.repositories.base_repository import BaseRepository

class TenantRepository(BaseRepository[Tenant]):
    """Repositorio para tenants"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Tenant, db)
