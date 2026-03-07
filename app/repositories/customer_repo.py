from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from .base_repository import BaseRepository
from ..models import Customer
from ..core.pagination import PaginationParams


class CustomerRepository(BaseRepository[Customer]):
    """Repositorio para clientes"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Customer, db)
    
    async def get_by_document(self, document_number: str, tenant_id: int) -> Optional[Customer]:
        """Obtiene un cliente por número de documento"""
        query = select(Customer).where(
            and_(
                Customer.document_number == document_number,
                Customer.tenant_id == tenant_id,
                Customer.is_deleted == False
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def search(
        self,
        search_term: str,
        tenant_id: int,
        pagination: Optional[PaginationParams] = None
    ) -> Tuple[List[Customer], int]:
        """Busca clientes por nombre, documento, email o teléfono"""
        query = select(Customer).where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.is_deleted == False,
                or_(
                    Customer.name.ilike(f"%{search_term}%"),
                    Customer.document_number.ilike(f"%{search_term}%"),
                    Customer.email.ilike(f"%{search_term}%"),
                    Customer.phone.ilike(f"%{search_term}%")
                )
            )
        )
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, Customer)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
    
    async def get_filtered(
        self,
        tenant_id: int,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        pagination: Optional[PaginationParams] = None
    ) -> Tuple[List[Customer], int]:
        """Obtiene clientes aplicando búsqueda y filtros de estado de forma combinada"""
        conditions = [
            Customer.tenant_id == tenant_id,
            Customer.is_deleted == False
        ]
        
        if search:
            conditions.append(or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.document_number.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%")
            ))
            
        if is_active is not None:
            conditions.append(Customer.is_active == is_active)

        if start_date:
            conditions.append(Customer.created_at >= start_date)
            
        if end_date:
            conditions.append(Customer.created_at <= end_date)
            
        query = select(Customer).where(and_(*conditions)).order_by(Customer.name.asc())
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, Customer)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)

    async def get_active_customers(self, tenant_id: int) -> List[Customer]:
        """Obtiene clientes activos"""
        query = select(Customer).where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.is_active == True,
                Customer.is_deleted == False
            )
        ).order_by(Customer.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
