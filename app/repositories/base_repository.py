from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.pagination import PaginationParams, paginate

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Repositorio base genérico con operaciones CRUD comunes"""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: int, tenant_id: Optional[int] = None) -> Optional[ModelType]:
        """Obtiene un registro por ID"""
        query = select(self.model).where(self.model.id == id)
        
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        tenant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Obtiene todos los registros con filtros opcionales"""
        query = select(self.model)
        
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        # Aplicar filtros adicionales
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        # Aplicar soft delete filter si existe
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_paginated(
        self,
        pagination: PaginationParams,
        tenant_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[ModelType], int]:
        """Obtiene registros paginados"""
        query = select(self.model)
        
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        # Aplicar filtros
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)
        
        # Aplicar soft delete filter
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        return await paginate(self.db, query, pagination, self.model)
    
    async def _record_audit(
        self,
        action: str,
        entity_id: int,
        tenant_id: int,
        user_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ):
        """Graba un log de auditoría"""
        try:
            from ..models.audit_log import AuditLog
            
            # Sanitizar valores para JSON
            old_sanitized = self._json_serializable(old_values) if old_values else None
            new_sanitized = self._json_serializable(new_values) if new_values else None

            audit_log = AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                entity_type=self.model.__name__,
                entity_id=entity_id,
                old_values=old_sanitized,
                new_values=new_sanitized,
                description=description
            )
            self.db.add(audit_log)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error grabando auditoría: {e}")

    def _json_serializable(self, data: Any) -> Any:
        """Convierte tipos no serializables (date, datetime, Decimal) a formatos JSON-friendly"""
        from datetime import date, datetime
        from decimal import Decimal

        if isinstance(data, dict):
            return {k: self._json_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._json_serializable(i) for i in data]
        elif isinstance(data, (datetime, date)):
            return data.isoformat()
        elif isinstance(data, Decimal):
            return float(data)
        return data

    async def create(self, obj_in: Dict[str, Any], user_id: Optional[int] = None) -> ModelType:
        """Crea un nuevo registro con auditoría opcional"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        
        if user_id and hasattr(db_obj, 'tenant_id'):
            await self._record_audit(
                action="CREATE",
                entity_id=db_obj.id,
                tenant_id=db_obj.tenant_id,
                user_id=user_id,
                new_values=obj_in
            )
            
        return db_obj
    
    async def update(self, id: int, obj_in: Dict[str, Any], tenant_id: Optional[int] = None, user_id: Optional[int] = None) -> Optional[ModelType]:
        """Actualiza un registro existente con auditoría opcional"""
        # Para auditoría necesitamos los valores viejos
        old_obj = await self.get_by_id(id, tenant_id)
        if not old_obj:
            return None
            
        old_values = {c.name: getattr(old_obj, c.name) for c in old_obj.__table__.columns if c.name in obj_in}
        
        query = update(self.model).where(self.model.id == id)
        
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        query = query.values(**obj_in).execution_options(synchronize_session="fetch")
        
        await self.db.execute(query)
        await self.db.flush()
        
        if user_id and tenant_id:
            await self._record_audit(
                action="UPDATE",
                entity_id=id,
                tenant_id=tenant_id,
                user_id=user_id,
                old_values=old_values,
                new_values=obj_in
            )
        
        return await self.get_by_id(id, tenant_id)
    
    async def delete(self, id: int, tenant_id: Optional[int] = None, user_id: Optional[int] = None, soft: bool = True) -> bool:
        """Elimina un registro con auditoría opcional"""
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return False
            
        if soft and hasattr(obj, 'soft_delete'):
            obj.soft_delete()
            await self.db.flush()
        else:
            query = delete(self.model).where(self.model.id == id)
            if tenant_id is not None and hasattr(self.model, 'tenant_id'):
                query = query.where(self.model.tenant_id == tenant_id)
            result = await self.db.execute(query)
            await self.db.flush()
            if result.rowcount == 0:
                return False

        if user_id and tenant_id:
            await self._record_audit(
                action="DELETE",
                entity_id=id,
                tenant_id=tenant_id,
                user_id=user_id,
                description=f"Eliminado via {'soft' if soft else 'hard'} delete"
            )
            
        return True
    
    async def count(self, tenant_id: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> int:
        """Cuenta registros con filtros opcionales"""
        query = select(func.count()).select_from(self.model)
        
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def exists(self, id: int, tenant_id: Optional[int] = None) -> bool:
        """Verifica si un registro existe"""
        query = select(func.count()).select_from(self.model).where(self.model.id == id)
        
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0
