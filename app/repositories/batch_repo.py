from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base_repository import BaseRepository
from ..models.product_batch import ProductBatch
from ..models.product import Product
from typing import List, Optional
from datetime import date

class BatchRepository(BaseRepository[ProductBatch]):
    def __init__(self, db: AsyncSession):
        super().__init__(ProductBatch, db)

    async def get_active_batches_by_product(self, product_id: int, tenant_id: int) -> List[ProductBatch]:
        """Obtiene lotes activos de un producto que tengan stock > 0, ordenados por vencimiento"""
        query = select(ProductBatch).where(
            ProductBatch.product_id == product_id,
            ProductBatch.tenant_id == tenant_id,
            ProductBatch.is_active == True,
            ProductBatch.current_quantity > 0
        ).order_by(ProductBatch.expiration_date.asc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_batch(self, tenant_id: int, batch_data) -> ProductBatch:
        """Crea un nuevo lote y actualiza el stock general del producto"""
        new_batch = ProductBatch(
            tenant_id=tenant_id,
            product_id=batch_data.product_id,
            batch_number=batch_data.batch_number,
            expiration_date=batch_data.expiration_date,
            initial_quantity=batch_data.initial_quantity,
            current_quantity=batch_data.initial_quantity,
            is_active=batch_data.is_active
        )
        self.db.add(new_batch)
        
        # Actualizar stock general del producto
        result = await self.db.execute(
            select(Product).where(Product.id == batch_data.product_id, Product.tenant_id == tenant_id)
        )
        product = result.scalar_one_or_none()
        if product:
            product.stock += batch_data.initial_quantity
        
        await self.db.flush()
        return new_batch
