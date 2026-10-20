from fastapi import APIRouter

from app.modules.identity.presentation.http import router as auth_http
from app.modules.identity.presentation.http import roles, tenant, users

router = APIRouter()
router.include_router(auth_http.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(tenant.router, prefix="/tenant", tags=["tenant"])
router.include_router(roles.router, prefix="/roles", tags=["roles"])
