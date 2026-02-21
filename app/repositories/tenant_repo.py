from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import Tenant
from .base_repository import BaseRepository

class TenantRepository(BaseRepository[Tenant]):
    """Repositorio para tenants"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Tenant, db)
