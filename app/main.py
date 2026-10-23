from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager
from app.presentation.api.router import register_routers
from app.infrastructure.config import settings
from app.infrastructure.logging import setup_logging
from app.infrastructure.cache import cache_manager
from app.domain.shared.errors import ConflictError, DomainError, ForbiddenError, NotFoundError
from app.presentation.middleware import ContextMiddleware
from app.infrastructure.persistence.audit_listener import setup_audit_listeners
from app.infrastructure.security.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.infrastructure.persistence.database import Base, engine
from app.infrastructure.persistence.bootstrap import bootstrap_reference_data
import logging
import sentry_sdk
from prometheus_fastapi_instrumentator import Instrumentator


# Configurar logging
setup_logging(settings.log_level, settings.environment)
logger = logging.getLogger(__name__)

# Configurar Sentry
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    logger.info("Sentry instrumentado correctamente")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo de eventos de inicio y cierre"""
    # Startup
    logger.info("Iniciando aplicación...")
    
    # Configurar Listeners de auditoría
    logger.info("Configurando escuchadores de auditoría SQLAlchemy...")
    setup_audit_listeners(Base)
    
    async with engine.begin() as conn:
        await bootstrap_reference_data(conn)

    await cache_manager.connect()
    logger.info("Aplicación iniciada correctamente")
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación...")
    await cache_manager.disconnect()
    logger.info("Aplicación cerrada")


_docs_enabled = settings.enable_docs and settings.environment.lower() != "production"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Sistema de inventario multi-tenant con FastAPI",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middlewares
app.add_middleware(ContextMiddleware)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if settings.environment.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# CORS
logger.info(f"Habilitando CORS para origenes: {settings.cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(DomainError)
async def domain_exception_handler(request: Request, exc: DomainError):
    """Traduce errores de dominio (puros) a HTTP: NotFound→404, Conflict→409, resto→400"""
    if isinstance(exc, NotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ForbiddenError):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ConflictError):
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_400_BAD_REQUEST
    return JSONResponse(status_code=code, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador de excepciones generales"""
    logger.error(f"Error no manejado: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"}
    )


register_routers(app)

# Servir archivos estáticos
os.makedirs("static/avatars", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Instrumentación de Prometheus
if settings.prometheus_enabled:
    Instrumentator().instrument(app).expose(app)
    logger.info("Prometheus instrumentado correctamente en /metrics")


@app.get("/")
async def root():
    return {
        "message": "Inventory SaaS API",
        "version": settings.app_version,
        "environment": settings.environment
    }
