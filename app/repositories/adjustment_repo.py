from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.adjustment import InventoryAdjustment, AdjustmentReason
from ..models.product import Product
from ..models.inventory_movement import InventoryMovement, MovementType
from ..schemas.adjustment import AdjustmentCreate
from typing import List, Optional

class AdjustmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, obj_in: AdjustmentCreate, user_id: int, tenant_id: int) -> InventoryAdjustment:
        # Get product and lock for update
        product_query = select(Product).where(Product.id == obj_in.product_id).with_for_update()
        result = await self.db.execute(product_query)
        product = result.scalar_one_or_none()
        
        if not product:
            raise ValueError("Product not found")

        # Calculate new stock
        stock_before = product.stock
        quantity_to_add = obj_in.quantity if obj_in.adjustment_type == "IN" else -obj_in.quantity
        stock_after = stock_before + quantity_to_add
        
        # Update product stock
        product.stock = stock_after
        
        # Create adjustment record
        adjustment = InventoryAdjustment(
            tenant_id=tenant_id,
            user_id=user_id,
            product_id=obj_in.product_id,
            adjustment_type=obj_in.adjustment_type,
            quantity=obj_in.quantity,
            reason=obj_in.reason,
            notes=obj_in.notes
        )
        self.db.add(adjustment)
        
        # Log inventory movement
        movement = InventoryMovement(
            tenant_id=tenant_id,
            product_id=obj_in.product_id,
            user_id=user_id,
            movement_type=MovementType.ADJUSTMENT,
            quantity=int(quantity_to_add),
            stock_before=int(stock_before),
            stock_after=int(stock_after),
            unit_cost=product.cost,
            reference=f"ADJ-{obj_in.reason}",
            notes=obj_in.notes
        )
        self.db.add(movement)
        
        await self.db.flush()
        await self.db.refresh(adjustment)
        return adjustment

    async def get_all(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[InventoryAdjustment]:
        query = select(InventoryAdjustment).where(InventoryAdjustment.tenant_id == tenant_id)\
            .offset(skip).limit(limit).order_by(InventoryAdjustment.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
