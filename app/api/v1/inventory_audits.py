from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...models import get_db
from ...dependencies import get_current_user, require_permission
from ...models.user import User
from ...services.inventory_audit_service import InventoryAuditService
from ...schemas.inventory_audit import (
    InventoryAuditCreate,
    InventoryAuditOut,
    InventoryAuditItemCreate,
    InventoryAuditItemOut
)
from typing import List

router = APIRouter()
 
@router.get("", response_model=List[InventoryAuditOut])
async def list_audits(
    current_user: User = Depends(require_permission("inventory:audits")),
    db: AsyncSession = Depends(get_db)
):
    from ...repositories.inventory_audit_repo import InventoryAuditRepository
    repo = InventoryAuditRepository(db)
    return await repo.get_recent(current_user.tenant_id)

@router.post("", response_model=InventoryAuditOut)
async def start_audit(
    request: InventoryAuditCreate,
    current_user: User = Depends(require_permission("inventory:audits")),
    db: AsyncSession = Depends(get_db)
):
    service = InventoryAuditService(db)
    return await service.start_audit(
        branch_id=request.branch_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        notes=request.notes
    )

@router.post("/{audit_id}/items", response_model=InventoryAuditItemOut)
async def add_audit_item(
    audit_id: int,
    request: InventoryAuditItemCreate,
    current_user: User = Depends(require_permission("inventory:audits")),
    db: AsyncSession = Depends(get_db)
):
    service = InventoryAuditService(db)
    return await service.add_counted_item(
        audit_id=audit_id,
        product_id=request.product_id,
        counted_stock=request.counted_stock,
        tenant_id=current_user.tenant_id,
        notes=request.notes
    )

@router.post("/{audit_id}/complete", response_model=InventoryAuditOut)
async def complete_audit(
    audit_id: int,
    current_user: User = Depends(require_permission("inventory:audits")),
    db: AsyncSession = Depends(get_db)
):
    service = InventoryAuditService(db)
    return await service.complete_audit(audit_id, current_user.tenant_id)

@router.get("/{audit_id}", response_model=InventoryAuditOut)
async def get_audit(
    audit_id: int,
    current_user: User = Depends(require_permission("inventory:audits")),
    db: AsyncSession = Depends(get_db)
):
    from ...repositories.inventory_audit_repo import InventoryAuditRepository
    repo = InventoryAuditRepository(db)
    audit = await repo.get_with_items(audit_id, current_user.tenant_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return audit
