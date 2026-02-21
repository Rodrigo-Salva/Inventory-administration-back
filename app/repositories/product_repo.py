from typing import List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .base_repository import BaseRepository
from ..models import Product
from ..core.pagination import PaginationParams


class ProductRepository(BaseRepository[Product]):
    """Repositorio para productos con métodos especializados"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Product, db)
    
    async def get_by_sku(self, sku: str, tenant_id: int) -> Optional[Product]:
        """Obtiene un producto por SKU"""
        query = select(Product).where(
            and_(
                Product.sku == sku,
                Product.tenant_id == tenant_id,
                Product.is_deleted == False
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_barcode(self, barcode: str, tenant_id: int) -> Optional[Product]:
        """Obtiene un producto por código de barras"""
        query = select(Product).where(
            and_(
                Product.barcode == barcode,
                Product.tenant_id == tenant_id,
                Product.is_deleted == False
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def search(
        self,
        search_term: str,
        tenant_id: int,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Product], int]:
        """Busca productos por nombre, SKU o código de barras"""
        query = select(Product).where(
            and_(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False,
                or_(
                    Product.name.ilike(f"%{search_term}%"),
                    Product.sku.ilike(f"%{search_term}%"),
                    Product.barcode.ilike(f"%{search_term}%") if search_term else False
                )
            )
        ).options(
            selectinload(Product.category),
            selectinload(Product.supplier)
        )
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, Product)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
    
    async def get_low_stock_products(self, tenant_id: int) -> List[Product]:
        """Obtiene productos con stock bajo o sin stock"""
        query = select(Product).where(
            and_(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False,
                Product.is_active == 1,
                Product.stock <= Product.min_stock
            )
        ).order_by(Product.stock.asc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_out_of_stock_products(self, tenant_id: int) -> List[Product]:
        """Obtiene productos sin stock"""
        query = select(Product).where(
            and_(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False,
                Product.is_active == 1,
                Product.stock <= 0
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_category(
        self,
        category_id: int,
        tenant_id: int,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Product], int]:
        """Obtiene productos por categoría"""
        query = select(Product).where(
            and_(
                Product.tenant_id == tenant_id,
                Product.category_id == category_id,
                Product.is_deleted == False
            )
        ).options(selectinload(Product.supplier))
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, Product)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
    
    async def get_by_supplier(
        self,
        supplier_id: int,
        tenant_id: int
    ) -> List[Product]:
        """Obtiene productos por proveedor"""
        query = select(Product).where(
            and_(
                Product.tenant_id == tenant_id,
                Product.supplier_id == supplier_id,
                Product.is_deleted == False
            )
        ).options(selectinload(Product.category))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_active_products(
        self,
        tenant_id: int,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Product], int]:
        """Obtiene productos activos"""
        query = select(Product).where(
            and_(
                Product.tenant_id == tenant_id,
                Product.is_active == 1,
                Product.is_deleted == False
            )
        ).options(
            selectinload(Product.category),
            selectinload(Product.supplier)
        )
        
        if pagination:
            from ..core.pagination import paginate
            return await paginate(self.db, query, pagination, Product)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, len(items)
    
    async def get_all_with_relations(
        self,
        tenant_id: int,
        limit: int = 1000
    ) -> List[Product]:
        """Obtiene todos los productos con sus relaciones cargadas"""
        query = select(Product).where(
            and_(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False
            )
        ).options(
            selectinload(Product.category),
            selectinload(Product.supplier)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_stock(self, product_id: int, new_stock: int, tenant_id: int) -> Optional[Product]:
        """Actualiza el stock de un producto"""
        product = await self.get_by_id(product_id, tenant_id)
        if product:
            product.stock = new_stock
            await self.db.flush()
            await self.db.refresh(product)
        return product