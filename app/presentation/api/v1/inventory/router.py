from fastapi import APIRouter
from app.presentation.api.v1.inventory import adjustments
from app.presentation.api.v1.inventory import barcodes
from app.presentation.api.v1.inventory import branches
from app.presentation.api.v1.inventory import inventory
from app.presentation.api.v1.inventory import inventory_audits
from app.presentation.api.v1.inventory import stock_transfers

router = APIRouter()
router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
router.include_router(adjustments.router, prefix="/adjustments", tags=["adjustments"])
router.include_router(branches.router, prefix="/branches", tags=["branches"])
router.include_router(stock_transfers.router, prefix="/stock-transfers", tags=["stock-transfers"])
router.include_router(inventory_audits.router, prefix="/inventory-audits", tags=["inventory-audits"])
router.include_router(barcodes.router, prefix="/barcodes", tags=["barcodes"])
