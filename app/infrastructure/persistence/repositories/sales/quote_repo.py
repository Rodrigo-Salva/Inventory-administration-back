from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload, selectinload
from app.infrastructure.persistence.repositories.base_repository import BaseRepository
from app.infrastructure.persistence.models.sales.quote import Quote, QuoteItem, QuoteStatus
from app.infrastructure.persistence.models.catalog.product import Product
from app.infrastructure.persistence.models.sales.customer import Customer
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from app.application.shared.pagination import PaginationParams

class QuoteRepository(BaseRepository[Quote]):
    def __init__(self, db: AsyncSession):
        super().__init__(Quote, db)

    async def get_by_id(self, id: int, tenant_id: Optional[int] = None) -> Optional[Quote]:
        """Obtiene una cotización con sus items y productos cargados"""
        query = select(Quote).options(
            joinedload(Quote.items).joinedload(QuoteItem.product)
        ).where(Quote.id == id)
        
        if tenant_id is not None:
            query = query.where(Quote.tenant_id == tenant_id)
            
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_quotes_paginated(
        self, 
        tenant_id: int, 
        pagination: PaginationParams,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Quote], int]:
        query = select(Quote).options(
            selectinload(Quote.items).selectinload(QuoteItem.product),
            selectinload(Quote.user),
            selectinload(Quote.customer)
        ).where(Quote.tenant_id == tenant_id)

        if customer_id:
            query = query.where(Quote.customer_id == customer_id)

        if search:
            clean_search = search.upper().replace("COT-", "").strip()
            if clean_search.isdigit():
                query = query.where(Quote.id == int(clean_search))
            else:
                customer_search = select(Customer.id).where(Customer.name.ilike(f"%{search}%"))
                query = query.where(Quote.customer_id.in_(customer_search))

        if start_date:
            query = query.where(Quote.created_at >= start_date)
        if end_date:
            query = query.where(Quote.created_at <= end_date)
        if status:
            query = query.where(Quote.status == status)

        query = query.order_by(Quote.created_at.desc())
        
        from app.infrastructure.persistence.pagination import paginate
        return await paginate(self.db, query, pagination, Quote)
