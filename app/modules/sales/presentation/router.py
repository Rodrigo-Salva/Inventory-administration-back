from fastapi import APIRouter
from app.api.v1 import credits, customers, loyalty, payments, pos, quotes, sales

router = APIRouter()
router.include_router(sales.router, prefix="/sales", tags=["sales"])
router.include_router(pos.router, prefix="/pos", tags=["pos"])
router.include_router(customers.router, prefix="/customers", tags=["customers"])
router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
router.include_router(credits.router, prefix="/credits", tags=["credits"])
router.include_router(loyalty.router, prefix="/loyalty", tags=["loyalty"])
router.include_router(payments.router, prefix="/payments", tags=["payments"])
