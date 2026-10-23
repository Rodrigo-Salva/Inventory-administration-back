from fastapi import APIRouter
from app.presentation.api.v1.catalog import categories
from app.presentation.api.v1.catalog import product_batches
from app.presentation.api.v1.catalog import products
from app.presentation.api.v1.catalog import suppliers

router = APIRouter()
router.include_router(products.router, prefix="/products", tags=["products"])
router.include_router(categories.router, prefix="/categories", tags=["categories"])
router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
router.include_router(product_batches.router, prefix="/product-batches", tags=["product-batches"])
