from fastapi import APIRouter
from app.modules.purchasing.presentation.http import expenses, purchases

router = APIRouter()
router.include_router(purchases.router, prefix="/purchases", tags=["purchases"])
router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
