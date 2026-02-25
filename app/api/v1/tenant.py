from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.base import get_db
from ...dependencies import get_current_admin, get_current_tenant, get_current_user
from ...repositories.tenant_repo import TenantRepository
from ...schemas.tenant import TenantOut, TenantUpdate
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/me", response_model=TenantOut)
async def get_my_tenant(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene la información del tenant actual"""
    repo = TenantRepository(db)
    tenant = await repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.patch("/me", response_model=TenantOut)
async def update_my_tenant(
    tenant_data: TenantUpdate,
    admin: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza la información del tenant (solo admins)"""
    repo = TenantRepository(db)
    
    updated_tenant = await repo.update(
        admin.tenant_id, 
        tenant_data.model_dump(exclude_unset=True)
    )
    await db.commit()
    await db.refresh(updated_tenant)
    
    logger.info(f"Tenant actualizado: {admin.tenant_id}")
    return updated_tenant
