"""Registro explícito de módulos HTTP del monolito.

`main` solo compone la aplicación. Los routers heredados se registran aquí
mientras se trasladan gradualmente a sus respectivos paquetes de `modules`.
"""

from fastapi import FastAPI

from app.infrastructure.config import settings
from app.presentation.api.v1.catalog import router as catalog_router
from app.presentation.api.v1.identity import router as identity_router
from app.presentation.api.v1.integrations import router as integrations_router
from app.presentation.api.v1.inventory import router as inventory_router
from app.presentation.api.v1.purchasing import router as purchasing_router
from app.presentation.api.v1.platform import health as platform_api
from app.presentation.api.v1.reporting import router as reporting_router
from app.presentation.api.v1.sales import router as sales_router


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
