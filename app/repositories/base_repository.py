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
    
    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Crea un nuevo registro"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, id: int, obj_in: Dict[str, Any], tenant_id: Optional[int] = None) -> Optional[ModelType]:
        """Actualiza un registro existente"""
        query = update(self.model).where(self.model.id == id)
        
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        query = query.values(**obj_in).execution_options(synchronize_session="fetch")
        
        await self.db.execute(query)
        await self.db.flush()
        
        return await self.get_by_id(id, tenant_id)
    
    async def delete(self, id: int, tenant_id: Optional[int] = None, soft: bool = True) -> bool:
        """Elimina un registro (soft delete por defecto)"""
        if soft and hasattr(self.model, 'soft_delete'):
            # Soft delete
            obj = await self.get_by_id(id, tenant_id)
            if obj:
                obj.soft_delete()
                await self.db.flush()
                return True
            return False
        else:
            # Hard delete
            query = delete(self.model).where(self.model.id == id)
            
            if tenant_id is not None and hasattr(self.model, 'tenant_id'):
                query = query.where(self.model.tenant_id == tenant_id)
            
            result = await self.db.execute(query)
            await self.db.flush()
            return result.rowcount > 0
    
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
