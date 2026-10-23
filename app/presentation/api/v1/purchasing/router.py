from fastapi import APIRouter
from app.presentation.api.v1.purchasing import expenses
from app.presentation.api.v1.purchasing import purchases

router = APIRouter()
router.include_router(purchases.router, prefix="/purchases", tags=["purchases"])
router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
