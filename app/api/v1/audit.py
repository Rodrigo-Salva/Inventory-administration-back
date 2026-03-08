from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from ...dependencies import get_db_session, get_current_user, require_permission
from ...repositories.audit_repo import AuditLogRepository
from ...core.pagination import PaginationParams
from ...models.user import User

router = APIRouter()

@router.get("/", dependencies=[Depends(require_permission("settings:manage"))])
async def get_audit_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Obtiene el historial de auditoría del tenant"""
    repo = AuditLogRepository(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    
    logs, total = await repo.get_by_tenant(
        tenant_id=current_user.tenant_id,
        pagination=pagination,
        user_id=user_id,
        action=action,
        entity_type=entity_type
    )
    
    return {
        "items": logs,
        "total": total,
        "page": page,
        "page_size": page_size
    }
