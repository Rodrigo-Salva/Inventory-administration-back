from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.database import get_db
from app.presentation.dependencies import get_current_user, require_permission
from app.infrastructure.persistence.models.identity.user import User
from app.application.inventory.stock_use_cases import CompleteAudit, CountAuditItem, StartAudit
from app.infrastructure.persistence.repositories.inventory.inventory_audit_repo import InventoryAuditRepository
from app.presentation.api.v1.inventory.deps import (
    get_complete_audit, get_count_audit_item, get_start_audit,
    to_complete_audit, to_count_item, to_start_audit,
)
from app.presentation.schemas.inventory.inventory_audit import InventoryAuditCreate, InventoryAuditOut, InventoryAuditItemCreate, InventoryAuditItemOut
from typing import List

router = APIRouter()
 
@router.get("", response_model=List[InventoryAuditOut])
async def list_audits(
    current_user: User = Depends(require_permission("inventory:audits")),
    db: AsyncSession = Depends(get_db)
):
    repo = InventoryAuditRepository(db)
    return await repo.get_recent(current_user.tenant_id)

@router.post("", response_model=InventoryAuditOut)
async def start_audit(
    request: InventoryAuditCreate,
    current_user: User = Depends(require_permission("inventory:audits")),
    use_case: StartAudit = Depends(get_start_audit),
    db: AsyncSession = Depends(get_db)
):
    audit_id = await use_case.execute(to_start_audit(request, current_user.tenant_id, current_user.id))
    return await InventoryAuditRepository(db).get_with_items(audit_id, current_user.tenant_id)

@router.post("/{audit_id}/items", response_model=InventoryAuditItemOut)
async def add_audit_item(
    audit_id: int,
    request: InventoryAuditItemCreate,
    current_user: User = Depends(require_permission("inventory:audits")),
    use_case: CountAuditItem = Depends(get_count_audit_item),
    db: AsyncSession = Depends(get_db)
):
    item_id = await use_case.execute(to_count_item(audit_id, request, current_user.tenant_id))
    return await InventoryAuditRepository(db).get_item_with_product(item_id)

@router.post("/{audit_id}/complete", response_model=InventoryAuditOut)
async def complete_audit(
    audit_id: int,
    current_user: User = Depends(require_permission("inventory:audits")),
    use_case: CompleteAudit = Depends(get_complete_audit),
    db: AsyncSession = Depends(get_db)
):
    await use_case.execute(to_complete_audit(audit_id, current_user.tenant_id, current_user.id))
    return await InventoryAuditRepository(db).get_with_items(audit_id, current_user.tenant_id)

@router.get("/{audit_id}", response_model=InventoryAuditOut)
async def get_audit(
    audit_id: int,
    current_user: User = Depends(require_permission("inventory:audits")),
    db: AsyncSession = Depends(get_db)
):
    repo = InventoryAuditRepository(db)
    audit = await repo.get_with_items(audit_id, current_user.tenant_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return audit
