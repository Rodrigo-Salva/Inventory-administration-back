from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from .api.v1 import auth, products, inventory, health, categories, suppliers
from .core.config import settings
from .core.logging_config import setup_logging
from .core.cache import cache_manager
from .core.exceptions import InventoryBaseException
import logging


# Configurar logging
setup_logging(settings.log_level, settings.environment)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo de eventos de inicio y cierre"""
    # Startup
    logger.info("Iniciando aplicación...")
    await cache_manager.connect()
    logger.info("Aplicación iniciada correctamente")
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación...")
    await cache_manager.disconnect()
    logger.info("Aplicación cerrada")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Sistema de inventario multi-tenant con FastAPI",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend React
        "http://localhost:8000",  # Backend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(InventoryBaseException)
async def inventory_exception_handler(request: Request, exc: InventoryBaseException):
    """Manejador de excepciones personalizadas"""
    logger.warning(f"Excepción de inventario: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador de excepciones generales"""
    logger.error(f"Error no manejado: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"}
    )


# Routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["suppliers"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["inventory"])


@app.get("/")
async def root():
    return {
        "message": "Inventory SaaS API",
        "version": settings.app_version,
        "environment": settings.environment
    }