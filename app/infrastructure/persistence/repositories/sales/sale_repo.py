from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.application.shared.pagination import PaginationParams
from app.infrastructure.persistence.models.catalog.product import Product
from app.infrastructure.persistence.models.sales.sale import Sale, SaleItem
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class SaleRepository(BaseRepository[Sale]):
    def __init__(self, db: AsyncSession):
        super().__init__(Sale, db)

    async def get_by_id(self, id: int, tenant_id: Optional[int] = None) -> Optional[Sale]:
        """Obtiene una venta con sus items, productos, cliente y usuario cargados"""
        query = select(Sale).options(
            joinedload(Sale.items).joinedload(SaleItem.product),
            joinedload(Sale.customer),
            joinedload(Sale.user)
        ).where(Sale.id == id)
        
        if tenant_id is not None:
            query = query.where(Sale.tenant_id == tenant_id)
            
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_sales_paginated(
        self, 
        tenant_id: int, 
        pagination: PaginationParams,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        search: Optional[str] = None,
        seller_id: Optional[int] = None
    ) -> tuple[List[Sale], int]:
        query = select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.customer),
            selectinload(Sale.user)
        ).where(Sale.tenant_id == tenant_id)

        # Aplicar filtros
        if seller_id:
            query = query.where(Sale.user_id == seller_id)

        if search:
            # Buscar por ID si es número, o por nombre de producto en los items
            if search.isdigit():
                query = query.where(Sale.id == int(search))
            else:
                # Búsqueda por producto
                product_search = select(SaleItem.sale_id).join(Product).where(
                    and_(
                        SaleItem.product_id == Product.id,
                        Product.name.ilike(f"%{search}%")
                    )
                )
                query = query.where(Sale.id.in_(product_search))

        if start_date:
            query = query.where(Sale.created_at >= start_date)
        if end_date:
            query = query.where(Sale.created_at <= end_date)
        if status:
            query = query.where(Sale.status == status)
        if payment_method:
            query = query.where(Sale.payment_method == payment_method)

        query = query.order_by(Sale.created_at.desc())
        
        # Usar la utilidad paginate del sistema
        from app.infrastructure.persistence.pagination import paginate
        return await paginate(self.db, query, pagination, Sale)
