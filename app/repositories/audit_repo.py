from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .base_repository import BaseRepository
from ..models.audit_log import AuditLog
from ..core.pagination import PaginationParams


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repositorio para troncos de auditoría"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)
    
    async def get_by_tenant(
        self, 
        tenant_id: int, 
        pagination: PaginationParams,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> tuple[List[AuditLog], int]:
        """Obtiene logs de auditoría filtrados por tenant"""
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
            
        query = query.options(selectinload(AuditLog.user)).order_by(desc(AuditLog.created_at))
        
        from ..core.pagination import paginate
        return await paginate(self.db, query, pagination, AuditLog)

    async def create_log(
        self, 
        tenant_id: int, 
        user_id: Optional[int], 
        action: str, 
        entity_type: str, 
        entity_id: int,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Crea un nuevo registro de auditoría"""
        log_data = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "old_values": old_values,
            "new_values": new_values,
            "description": description,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        return await self.create(log_data)
