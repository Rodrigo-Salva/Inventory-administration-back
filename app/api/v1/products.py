from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from dependencies import get_current_tenant
from models.base import get_db
from models import Product
from schemas.product import ProductOut

router = APIRouter()

@router.get("/products", response_model=list[ProductOut])
async def list_products(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Product).where(Product.tenant_id == tenant_id)
    )
    return result.scalars().all()