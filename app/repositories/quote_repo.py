from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload, selectinload
from .base_repository import BaseRepository
from ..models.quote import Quote, QuoteItem, QuoteStatus
from ..models.product import Product
from ..models.customer import Customer
from ..core.exceptions import ProductNotFoundException
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from ..core.pagination import PaginationParams

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

    async def create_quote(self, tenant_id: int, user_id: int, quote_data) -> Quote:
        """Crea una cotización sin afectar stock"""
        total_amount = Decimal(0)
        quote_items = []
        
        new_quote = Quote(
            tenant_id=tenant_id,
            user_id=user_id,
            customer_id=quote_data.customer_id,
            valid_until=quote_data.valid_until,
            notes=quote_data.notes,
            total_amount=0
        )
        self.db.add(new_quote)
        await self.db.flush() # Para obtener el ID

        for item_data in quote_data.items:
            # Verificar producto
            result = await self.db.execute(
                select(Product).where(Product.id == item_data.product_id, Product.tenant_id == tenant_id)
            )
            product = result.scalar_one_or_none()
            
            if not product:
                raise ProductNotFoundException(item_data.product_id)
            
            subtotal = Decimal(str(item_data.quantity)) * Decimal(str(item_data.unit_price))
            total_amount += subtotal
            
            quote_item = QuoteItem(
                quote_id=new_quote.id,
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                subtotal=subtotal
            )
            quote_items.append(quote_item)

        new_quote.total_amount = total_amount
        self.db.add_all(quote_items)
        
        await self.db.commit()
        return await self.get_by_id(new_quote.id, tenant_id)

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
        
        from ..core.pagination import paginate
        return await paginate(self.db, query, pagination, Quote)
