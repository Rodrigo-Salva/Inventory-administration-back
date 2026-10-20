"""Registro explícito de módulos HTTP del monolito.

`main` solo compone la aplicación. Los routers heredados se registran aquí
mientras se trasladan gradualmente a sus respectivos paquetes de `modules`.
"""

from fastapi import FastAPI

from app.core.config import settings
from app.modules.catalog.presentation import router as catalog_router
from app.modules.identity.presentation import router as identity_router
from app.modules.integrations.presentation import router as integrations_router
from app.modules.inventory.presentation import router as inventory_router
from app.modules.purchasing.presentation import router as purchasing_router
from app.modules.platform.presentation import http as platform_api
from app.modules.reporting.presentation import router as reporting_router
from app.modules.sales.presentation import router as sales_router


def register_routers(app: FastAPI) -> None:
    """Monta los contratos HTTP conservando las rutas públicas existentes."""
    app.include_router(platform_api.router, prefix="/health", tags=["health"])
    app.include_router(identity_router.router, prefix=settings.api_v1_str)
    app.include_router(catalog_router.router, prefix=settings.api_v1_str)
    app.include_router(inventory_router.router, prefix=settings.api_v1_str)
    app.include_router(sales_router.router, prefix=settings.api_v1_str)
    app.include_router(purchasing_router.router, prefix=settings.api_v1_str)
    app.include_router(reporting_router.router, prefix=settings.api_v1_str)
    app.include_router(integrations_router.router, prefix=settings.api_v1_str)
