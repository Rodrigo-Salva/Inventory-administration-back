from fastapi import APIRouter

from app.presentation.api.v1.identity import auth as auth_http
from app.presentation.api.v1.identity import roles
from app.presentation.api.v1.identity import tenant
from app.presentation.api.v1.identity import users

router = APIRouter()
router.include_router(auth_http.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(tenant.router, prefix="/tenant", tags=["tenant"])
router.include_router(roles.router, prefix="/roles", tags=["roles"])
