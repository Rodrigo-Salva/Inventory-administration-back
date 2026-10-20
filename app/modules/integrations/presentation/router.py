from fastapi import APIRouter
from app.api.v1 import webhooks

router = APIRouter()
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
