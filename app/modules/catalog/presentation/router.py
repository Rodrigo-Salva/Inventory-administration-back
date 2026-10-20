from fastapi import APIRouter
from app.modules.catalog.presentation.http import categories, product_batches, products, suppliers

router = APIRouter()
router.include_router(products.router, prefix="/products", tags=["products"])
router.include_router(categories.router, prefix="/categories", tags=["categories"])
router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
router.include_router(product_batches.router, prefix="/product-batches", tags=["product-batches"])
