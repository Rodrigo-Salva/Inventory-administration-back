from fastapi import APIRouter
from app.presentation.api.v1.sales import credits
from app.presentation.api.v1.sales import customers
from app.presentation.api.v1.sales import loyalty
from app.presentation.api.v1.sales import payments
from app.presentation.api.v1.sales import pos
from app.presentation.api.v1.sales import quotes
from app.presentation.api.v1.sales import sales

router = APIRouter()
router.include_router(sales.router, prefix="/sales", tags=["sales"])
router.include_router(pos.router, prefix="/pos", tags=["pos"])
router.include_router(customers.router, prefix="/customers", tags=["customers"])
router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
router.include_router(credits.router, prefix="/credits", tags=["credits"])
router.include_router(loyalty.router, prefix="/loyalty", tags=["loyalty"])
router.include_router(payments.router, prefix="/payments", tags=["payments"])
