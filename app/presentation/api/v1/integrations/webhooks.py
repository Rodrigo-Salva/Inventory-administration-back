from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, HttpUrl

from app.infrastructure.persistence.database import get_db
from app.presentation.dependencies import get_current_tenant, require_role
from app.infrastructure.persistence.models.identity.user import User, UserRole
from app.infrastructure.persistence.models.integrations.webhook import Webhook
from app.infrastructure.persistence.repositories.integrations.webhook_repo import WebhookRepository
from app.infrastructure.config import settings
from app.infrastructure.security.url_safety import UnsafeUrlError, assert_public_http_url

router = APIRouter(tags=["Webhooks"])

class WebhookCreate(BaseModel):
    url: HttpUrl
    events: List[str]
    description: Optional[str] = None

class WebhookResponse(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.post("/", response_model=WebhookResponse)
async def create_webhook(
    webhook_in: WebhookCreate,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Registra un nuevo webhook para el tenant"""
    try:
        assert_public_http_url(
            str(webhook_in.url), allow_http=settings.environment.lower() != "production"
        )
    except UnsafeUrlError as e:
        raise HTTPException(status_code=422, detail=str(e))
    repo = WebhookRepository(db)
    webhook = await repo.create(
        tenant_id=tenant_id,
        url=str(webhook_in.url),
        events=webhook_in.events,
        description=webhook_in.description
    )
    return webhook

@router.get("/", response_model=List[WebhookResponse])
async def list_webhooks(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los webhooks registrados para el tenant"""
    repo = WebhookRepository(db)
    return await repo.get_by_tenant(tenant_id)

@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Elimina un webhook registrado"""
    repo = WebhookRepository(db)
    success = await repo.delete(webhook_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    return {"detail": "Webhook eliminado correctamente"}

@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    background_tasks: BackgroundTasks,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Envía un evento de prueba al webhook especificado"""
    from app.infrastructure.external.webhook_service import WebhookService
    from app.infrastructure.persistence.repositories.integrations.webhook_repo import WebhookRepository
    from fastapi import BackgroundTasks
    
    repo = WebhookRepository(db)
    webhook = await db.get(Webhook, webhook_id) # Usando direct get por simplicidad en el test
    
    if not webhook or webhook.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
        
    service = WebhookService(db)
    payload = {
        "message": "Este es un evento de prueba del sistema Inventory SaaS",
        "timestamp": datetime.now().isoformat(),
        "test": True
    }
    
    # Lo ejecutamos asíncronamente de forma segura
    from app.infrastructure.persistence.database import async_session
    background_tasks.add_task(
        WebhookService.trigger_test_webhook_task,
        webhook_id,
        payload,
        async_session
    )
    
    return {"detail": "Evento de prueba enviado"}
