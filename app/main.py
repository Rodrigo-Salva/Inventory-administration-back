from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager
from .api.v1 import auth, products, inventory, health, categories, suppliers, users, tenant, reports, sales, roles, customers, purchases, adjustments, audit, notifications, ai, expenses, branches, quotes, product_batches
from .core.config import settings
from .core.logging_config import setup_logging
from .core.cache import cache_manager
from .core.exceptions import InventoryBaseException
from .core.context_middleware import ContextMiddleware
from .core.audit_listener import setup_audit_listeners
from .models.base import Base
import logging


# Configurar logging
setup_logging(settings.log_level, settings.environment)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo de eventos de inicio y cierre"""
    # Startup
    logger.info("Iniciando aplicación...")
    
    # Configurar Listeners de auditoría
    logger.info("Configurando escuchadores de auditoría SQLAlchemy...")
    setup_audit_listeners(Base)
    
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

        logger.info("Creando tablas principales (sucursales)...")
        try:
            from .models.branch import Branch
            from .models.product_branch import ProductBranch
            # Tablas base que deben existir primero
            await conn.run_sync(Base.metadata.create_all, tables=[Branch.__table__])
            
            # Crear Sucursal Principal por defecto si no existe una para que no rompa el tenant
            await conn.execute(text("""
                INSERT INTO branches (tenant_id, name, is_active, is_deleted, created_at, updated_at)
                SELECT t.id, 'Sucursal Principal', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM tenants t
                WHERE NOT EXISTS (SELECT 1 FROM branches b WHERE b.tenant_id = t.id)
            """))
            logger.info("Tablas de sucursales verificadas")
        except Exception as e:
            logger.error(f"Error creando tablas de sucursales: {e}")

        logger.info("Creando tablas de ventas si no existen...")
        try:
            from .models.sale import Sale, SaleItem
            from .models.purchase import Purchase, PurchaseItem
            await conn.run_sync(Base.metadata.create_all, tables=[Sale.__table__, SaleItem.__table__, Purchase.__table__, PurchaseItem.__table__])
            # Asegurar que existe la columna status si no se creó
            try:
                await conn.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed'"))
            except Exception: pass
            
            # Migración Purchase
            try:
                await conn.execute(text("ALTER TABLE purchases ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id)"))
                
                # Asignar a la Sucursal Principal de cada tenant las compras existentes sin branch_id
                await conn.execute(text("""
                    UPDATE purchases p
                    SET branch_id = b.id
                    FROM branches b
                    WHERE p.tenant_id = b.tenant_id
                    AND b.name = 'Sucursal Principal'
                    AND p.branch_id IS NULL
                """))
            except Exception as e:
                logger.warning(f"Cuidado al sincronizar branch_id en Purchases: {e}")
                
            logger.info("Tablas de ventas verificadas/creadas")
        except Exception as e:
            logger.error(f"Error creando tablas de ventas: {e}")
        logger.info("Gestión de esquema de ventas completada")
        
        logger.info("Creando tabla de clientes si no existe...")
        try:
            from .models.customer import Customer
            await conn.run_sync(Base.metadata.create_all, tables=[Customer.__table__])
            # Asegurar campo customer_id en sales
            await conn.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_id INTEGER REFERENCES customers(id)"))
            logger.info("Tabla de clientes verificada")
        except Exception as e:
            logger.error(f"Error creando tabla de clientes: {e}")

        logger.info("Creando tabla de ajustes si no existe...")
        try:
            from .models.adjustment import InventoryAdjustment
            await conn.run_sync(Base.metadata.create_all, tables=[InventoryAdjustment.__table__])
            logger.info("Tabla de ajustes verificada")
        except Exception as e:
            logger.error(f"Error creando tabla de ajustes: {e}")

        logger.info("Creando tabla de gastos si no existe...")
        try:
            from .models.expense import Expense
            await conn.run_sync(Base.metadata.create_all, tables=[Expense.__table__])
            logger.info("Tabla de gastos verificada")
        except Exception as e:
            logger.error(f"Error creando tabla de gastos: {e}")

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
            await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS max_stock INTEGER"))
            await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
            logger.info("Verificación de columnas de productos completada")

            # Migración: Agregar branch_id a inventory_movements
            try:
                await conn.execute(text("ALTER TABLE inventory_movements ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id)"))
            except Exception: pass

            # Migración: Asegurar que ProductBranch exista para todos los productos de las sucursales principales
            logger.info("Migrando stock de productos hacia ProductBranch...")
            await conn.run_sync(Base.metadata.create_all, tables=[ProductBranch.__table__])
            await conn.execute(text("""
                INSERT INTO product_branches (product_id, branch_id, stock, min_stock, max_stock, created_at, updated_at)
                SELECT p.id, b.id, p.stock, p.min_stock, p.max_stock, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM products p
                JOIN branches b ON b.tenant_id = p.tenant_id
                WHERE b.name = 'Sucursal Principal'
                AND NOT EXISTS (
                    SELECT 1 FROM product_branches pb 
                    WHERE pb.product_id = p.id AND pb.branch_id = b.id
                )
            """))
            logger.info("Migración a ProductBranch completada")
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES roles(id)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id)"))
        except Exception as e:
            logger.error(f"Error creando tablas de roles/branch users: {e}")
            # Intentar solo la columna por si las tablas ya existían pero la columna no
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
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
            ("Ver Clientes", "customers:view", "customers"),
            ("Crear Clientes", "customers:create", "customers"),
            ("Editar Clientes", "customers:edit", "customers"),
            ("Eliminar Clientes", "customers:delete", "customers"),
            ("Ver Compras", "purchases:view", "purchases"),
            ("Crear Compras", "purchases:create", "purchases"),
            ("Recibir Compras", "purchases:receive", "purchases"),
            ("Anular Compras", "purchases:annul", "purchases"),
            ("Ver Ajustes de Inventario", "adjustments:view", "inventory"),
            ("Crear Ajustes de Inventario", "adjustments:create", "inventory"),
            ("Ver Gastos", "expenses:view", "expenses"),
            ("Registrar Gastos", "expenses:manage", "expenses"),
            ("Exportar Gastos", "expenses:export", "expenses"),
            ("Ver Predicciones IA", "ai:forecast", "ai"),
            ("Imprimir Etiquetas de Productos", "products:labels", "products"),
            ("Ver Sucursales", "branches:view", "branches"),
            ("Crear Sucursales", "branches:create", "branches"),
            ("Editar Sucursales", "branches:edit", "branches"),
            ("Eliminar Sucursales", "branches:delete", "branches"),
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

# Middlewares
app.add_middleware(ContextMiddleware)

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
app.include_router(branches.router, prefix=f"{settings.api_v1_str}/branches", tags=["branches"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(purchases.router, prefix="/api/v1/purchases", tags=["purchases"])
app.include_router(adjustments.router, prefix="/api/v1/adjustments", tags=["adjustments"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(expenses.router, prefix="/api/v1/expenses", tags=["expenses"])
app.include_router(quotes.router, prefix="/api/v1/quotes", tags=["quotes"])
app.include_router(product_batches.router, prefix="/api/v1/product-batches", tags=["product-batches"])

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