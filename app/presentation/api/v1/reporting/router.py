from fastapi import APIRouter
from app.presentation.api.v1.reporting import ai
from app.presentation.api.v1.reporting import audit
from app.presentation.api.v1.reporting import notifications
from app.presentation.api.v1.reporting import exports, reports

router = APIRouter()
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(exports.router, prefix="/reports", tags=["reports"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
