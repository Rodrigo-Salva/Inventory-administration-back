from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager
from .api.v1 import auth, products, inventory, health, categories, suppliers, users, tenant, reports, sales, roles
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
    
    # Auto-migración temporal para sincronizar tabla tenants
    from sqlalchemy import text
    from .models.base import engine
    async with engine.begin() as conn:
        logger.info("Sincronizando esquema de tenants...")
        columns = [
            ("tax_id", "VARCHAR(20)"), ("email", "VARCHAR(100)"), ("phone", "VARCHAR(20)"),
            ("website", "VARCHAR(100)"), ("address", "VARCHAR(255)"), ("city", "VARCHAR(100)"),
            ("state", "VARCHAR(100)"), ("country", "VARCHAR(100)"), ("logo_url", "VARCHAR(255)"),
            ("plan", "VARCHAR(20) DEFAULT 'free'"), ("expires_at", "TIMESTAMP WITH TIME ZONE")
        ]
        for col_name, col_type in columns:
            try:
                await conn.execute(text(f"ALTER TABLE tenants ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception:
                pass
        logger.info("Sincronización de tenants completada")
        
        logger.info("Sincronizando esquema de categorías...")
        try:
            # Nota: IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE es postgres specific
            # Si ya existe ignorará el error
            await conn.execute(text("ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
        except Exception:
            pass
        logger.info("Sincronización de categorías completada")

        logger.info("Creando tablas de ventas si no existen...")
        try:
            # Creación de tablas por si no existen (Alembic sería ideal, pero usamos esto por ahora)
            from .models.base import Base
            from .models.sale import Sale, SaleItem
            await conn.run_sync(Base.metadata.create_all, tables=[Sale.__table__, SaleItem.__table__])
            # Asegurar que existe la columna status si no se creó
            try:
                await conn.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed'"))
            except Exception: pass
            logger.info("Tablas de ventas verificadas/creadas")
        except Exception as e:
            logger.error(f"Error creando tablas de ventas: {e}")
        logger.info("Gestión de esquema de ventas completada")

        # 1. Crear tablas de Roles y Permisos (Separado para mayor compatibilidad)
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    codename VARCHAR(100) UNIQUE NOT NULL,
                    module VARCHAR(50) NOT NULL,
                    description VARCHAR(255)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER REFERENCES tenants(id),
                    name VARCHAR(100) NOT NULL,
                    description VARCHAR(255),
                    is_system BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
                    PRIMARY KEY (role_id, permission_id)
                );
            """))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES roles(id)"))
        except Exception as e:
            logger.error(f"Error creando tablas de roles: {e}")
            # Intentar solo la columna por si las tablas ya existían pero la columna no
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER"))
            except: pass

        # 2. Seed de Permisos fijos
        permissions_seed = [
            ("Ver Dashboard y Gráficos", "dashboard:view", "dashboard"),
            ("Ver Productos", "products:view", "products"),
            ("Crear Productos", "products:create", "products"),
            ("Editar Productos", "products:edit", "products"),
            ("Eliminar Productos", "products:delete", "products"),
            ("Descargar Catálogo Excel/PDF", "products:download", "products"),
            ("Ver Categorías", "categories:view", "categories"),
            ("Crear Categorías", "categories:create", "categories"),
            ("Editar Categorías", "categories:edit", "categories"),
            ("Eliminar Categorías", "categories:delete", "categories"),
            ("Ver Proveedores", "suppliers:view", "suppliers"),
            ("Crear Proveedores", "suppliers:create", "suppliers"),
            ("Editar Proveedores", "suppliers:edit", "suppliers"),
            ("Eliminar Proveedores", "suppliers:delete", "suppliers"),
            ("Ver Almacén/Stock", "inventory:view", "inventory"),
            ("Realizar Ajustes de Stock", "inventory:adjust", "inventory"),
            ("Ver Ventas (POS)", "sales:create", "sales"),
            ("Ver Historial de Ventas", "sales:view", "sales_history"),
            ("Anular Ventas del Historial", "sales:annul", "sales_history"),
            ("Ver Usuarios", "users:view", "users"),
            ("Crear Usuarios", "users:create", "users"),
            ("Editar Usuarios", "users:edit", "users"),
            ("Eliminar Usuarios", "users:delete", "users"),
            ("Ver Roles y Permisos", "roles:manage", "roles_permissions"),
            ("Configuración de Empresa", "settings:manage", "settings"),
            ("Ver Reportes Financieros", "reports:view", "reports"),
        ]
        
        for name, codename, module in permissions_seed:
            try:
                await conn.execute(text("""
                    INSERT INTO permissions (name, codename, module) 
                    VALUES (:name, :codename, :module) 
                    ON CONFLICT (codename) DO UPDATE SET 
                        module = EXCLUDED.module,
                        name = EXCLUDED.name
                """), {"name": name, "codename": codename, "module": module})
            except Exception: pass

        # 3. Gestión de Roles manual por el usuario
        logger.info("Sistema de roles listo para configuración manual")
            
        logger.info("Sincronización de usuarios completada")

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
logger.info(f"Habilitando CORS para origenes: {settings.cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["suppliers"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["inventory"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(tenant.router, prefix="/api/v1/tenant", tags=["tenant"])
app.include_router(reports.router, prefix=f"{settings.api_v1_str}/reports", tags=["reports"])
app.include_router(roles.router, prefix=f"{settings.api_v1_str}/roles")
app.include_router(sales.router, prefix="/api/v1/sales", tags=["sales"])

# Servir archivos estáticos
os.makedirs("static/avatars", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {
        "message": "Inventory SaaS API",
        "version": settings.app_version,
        "environment": settings.environment
    }