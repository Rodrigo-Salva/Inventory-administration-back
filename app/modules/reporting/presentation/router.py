from fastapi import APIRouter
from app.api.v1 import ai, audit, notifications, reports

router = APIRouter()
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
