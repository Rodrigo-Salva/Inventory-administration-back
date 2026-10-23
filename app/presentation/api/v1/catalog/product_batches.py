from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog import admin_use_cases as uc
from app.application.catalog.admin_dto import CreateBatchCommand
from app.domain.catalog.errors import ProductBatchNotFoundError
from app.infrastructure.logging import get_logger
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.catalog.batch_repo import BatchRepository
from app.presentation.api.v1.catalog.admin_deps import get_create_batch
from app.presentation.dependencies import require_permission
from app.presentation.schemas.catalog.product_batch import ProductBatchCreate, ProductBatchOut

logger = get_logger(__name__)
router = APIRouter()


async def _batch_or_404(db: AsyncSession, batch_id: int, tenant_id: int):
    batch = await BatchRepository(db).get_by_id(batch_id, tenant_id)
    if not batch:
        raise ProductBatchNotFoundError()
    return batch


@router.get("/product/{product_id}", response_model=List[ProductBatchOut])
async def list_product_batches(
    product_id: int,
    current_user: User = Depends(require_permission("batches:view")),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los lotes activos de un producto"""
    return await BatchRepository(db).get_active_batches_by_product(product_id, current_user.tenant_id)


@router.post("", response_model=ProductBatchOut, status_code=status.HTTP_201_CREATED)
async def create_product_batch(
    batch_in: ProductBatchCreate,
    current_user: User = Depends(require_permission("batches:manage")),
    use_case: uc.CreateBatch = Depends(get_create_batch),
    db: AsyncSession = Depends(get_db),
):
    """Crea un lote para un producto del tenant y aumenta el stock general"""
    batch_id = await use_case.execute(
        CreateBatchCommand(
            tenant_id=current_user.tenant_id,
            product_id=batch_in.product_id,
            batch_number=batch_in.batch_number,
            expiration_date=batch_in.expiration_date,
            initial_quantity=batch_in.initial_quantity,
            is_active=batch_in.is_active,
            user_id=current_user.id,
            branch_id=batch_in.branch_id,
        )
    )
    logger.info(f"Lote creado: {batch_id} para producto {batch_in.product_id}")
    return await _batch_or_404(db, batch_id, current_user.tenant_id)


@router.get("/{batch_id}", response_model=ProductBatchOut)
async def get_batch(
    batch_id: int,
    current_user: User = Depends(require_permission("batches:view")),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene un lote específico por ID"""
    return await _batch_or_404(db, batch_id, current_user.tenant_id)
