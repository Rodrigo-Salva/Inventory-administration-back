from fastapi import APIRouter
from app.presentation.api.v1.integrations import webhooks

router = APIRouter()
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
