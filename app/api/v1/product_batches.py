from typing import List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ...models import get_db
from ...dependencies import get_current_tenant, require_permission
from ...models.user import User
from ...repositories.batch_repo import BatchRepository
from ...schemas.product_batch import ProductBatchCreate, ProductBatchOut, ProductBatchUpdate
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/product/{product_id}", response_model=List[ProductBatchOut])
async def list_product_batches(
    product_id: int,
    current_user: User = Depends(require_permission("batches:view")),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los lotes activos de un producto"""
    repo = BatchRepository(db)
    tenant_id = current_user.tenant_id
    return await repo.get_active_batches_by_product(product_id, tenant_id)

@router.post("", response_model=ProductBatchOut, status_code=status.HTTP_201_CREATED)
async def create_product_batch(
    batch_in: ProductBatchCreate,
    current_user: User = Depends(require_permission("batches:manage")),
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo lote para un producto y aumenta el stock general"""
    repo = BatchRepository(db)
    tenant_id = current_user.tenant_id
    
    batch = await repo.create_batch(tenant_id, batch_in)
    await db.commit()
    await db.refresh(batch)
    
    logger.info(f"Lote creado: {batch.id} para producto {batch.product_id}")
    return batch

@router.get("/{batch_id}", response_model=ProductBatchOut)
async def get_batch(
    batch_id: int,
    current_user: User = Depends(require_permission("batches:view")),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un lote específico por ID"""
    repo = BatchRepository(db)
    batch = await repo.get_by_id(batch_id, tenant_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return batch
