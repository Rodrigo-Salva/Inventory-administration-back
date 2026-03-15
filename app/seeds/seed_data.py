"""
Script para poblar la base de datos con datos de ejemplo
Uso: python -m app.seeds.seed_data [--clean]
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Base, Tenant, User, Category, Supplier, Product
from app.models.role import Role, Permission
from app.models.user import UserRole
from app.seeds.data.categories import CATEGORIES
from app.seeds.data.suppliers import SUPPLIERS
from app.seeds.data.products import PRODUCTS


async def clean_database(engine, session: AsyncSession):
    """Limpia todos los datos de la base de datos recreando las tablas"""
    print("  Limpiando base de datos (recreando tablas)...")
    
    async with engine.begin() as conn:
        # Importante: Base.metadata necesita que todos los modelos estn cargados
        # lo cual ya ocurre arriba con los imports
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    print(" Base de datos recreada exitosamente")


async def create_tenant_and_user(session: AsyncSession):
    """Crea el tenant y usuario demo si no existen"""
    print("\n Verificando tenant y usuario...")
    
    # Verificar si el usuario ya existe
    from sqlalchemy import select
    result = await session.execute(select(User).where(User.email == "admin@demo.com"))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        print(f" Usuario demo ya existe: {existing_user.email}")
        return existing_user.tenant_id

    # Crear tenant
    tenant = Tenant(
        name="Inventory Administration",
        subdomain="demo"
    )
    session.add(tenant)
    await session.flush()
    
    # Crear usuario admin
    hashed_password = get_password_hash("demo123")
    user = User(
        tenant_id=tenant.id,
        email="admin@demo.com",
        hashed_password=hashed_password,
        is_admin=True
    )
    session.add(user)
    await session.commit()
    
    print(f"OK Tenant creado: {tenant.name} (ID: {tenant.id})")
    print(f"OK Usuario creado: {user.email} / password: demo123")
    
    return tenant.id


async def create_categories(session: AsyncSession, tenant_id: int):
    """Crea las categoras jerrquicas"""
    print("\n[INFO] Creando categoras...")
    
    category_map = {}  # code -> Category object
    
    # Primera pasada: crear categoras raz
    for cat_data in CATEGORIES:
        if cat_data["parent_code"] is None:
            # Verificar si ya existe
            from sqlalchemy import select
            res = await session.execute(select(Category).where(Category.code == cat_data["code"]))
            category = res.scalar_one_or_none()
            if category:
                category_map[cat_data["code"]] = category
                print(f"  - {cat_data['name']} (ya existe)")
                continue

            category = Category(
                tenant_id=tenant_id,
                name=cat_data["name"],
                code=cat_data["code"],
                description=cat_data.get("description"),
                display_order=cat_data.get("display_order", 0)
            )
            session.add(category)
            await session.flush()
            category_map[cat_data["code"]] = category
            print(f"   {category.name} ({category.code})")
    
    # Segunda pasada: crear categoras con padre
    for cat_data in CATEGORIES:
        if cat_data["parent_code"] is not None:
            # Verificar si ya existe
            from sqlalchemy import select
            res = await session.execute(select(Category).where(Category.code == cat_data["code"]))
            category = res.scalar_one_or_none()
            if category:
                category_map[cat_data["code"]] = category
                print(f"    - {cat_data['name']} (ya existe)")
                continue

            parent = category_map.get(cat_data["parent_code"])
            if parent:
                category = Category(
                    tenant_id=tenant_id,
                    name=cat_data["name"],
                    code=cat_data["code"],
                    description=cat_data.get("description"),
                    parent_id=parent.id,
                    display_order=cat_data.get("display_order", 0)
                )
                session.add(category)
                await session.flush()
                category_map[cat_data["code"]] = category
                print(f"    OK {category.name} ({category.code}) -> {parent.name}")
    
    await session.commit()
    print(f"OK {len(category_map)} categorias creadas")
    
    return category_map


async def create_suppliers(session: AsyncSession, tenant_id: int):
    """Crea los proveedores"""
    print("\nCreando proveedores...")
    
    supplier_map = {}  # code -> Supplier object
    
    for sup_data in SUPPLIERS:
        # Verificar si ya existe
        from sqlalchemy import select
        res = await session.execute(select(Supplier).where(Supplier.code == sup_data["code"]))
        supplier = res.scalar_one_or_none()
        if supplier:
            supplier_map[sup_data["code"]] = supplier
            print(f"  - {sup_data['name']} (ya existe)")
            continue

        supplier = Supplier(
            tenant_id=tenant_id,
            name=sup_data["name"],
            code=sup_data["code"],
            tax_id=sup_data.get("tax_id"),
            contact_name=sup_data.get("contact_name"),
            email=sup_data.get("email"),
            phone=sup_data.get("phone"),
            mobile=sup_data.get("mobile"),
            address=sup_data.get("address"),
            city=sup_data.get("city"),
            state=sup_data.get("state"),
            country=sup_data.get("country"),
            postal_code=sup_data.get("postal_code"),
            website=sup_data.get("website"),
            notes=sup_data.get("notes"),
            is_active=sup_data.get("is_active", True)
        )
        session.add(supplier)
        await session.flush()
        supplier_map[sup_data["code"]] = supplier
        print(f"   {supplier.name} ({supplier.code})")
    
    await session.commit()
    print(f" {len(supplier_map)} proveedores creados")
    
    return supplier_map


async def create_roles_and_permissions(session: AsyncSession, tenant_id: int):
    """Crea roles y permisos por defecto"""
    print("\n[INFO] Creando roles y permisos...")
    
    # 1. Definir permisos base
    permissions_data = [
        # Dashboard
        {"name": "Ver Dashboard", "codename": "dashboard:view", "module": "admin"},

        # Productos y Categoras
        {"name": "Ver Productos", "codename": "products:view", "module": "inventory"},
        {"name": "Crear Productos", "codename": "products:create", "module": "inventory"},
        {"name": "Editar Productos", "codename": "products:edit", "module": "inventory"},
        {"name": "Eliminar Productos", "codename": "products:delete", "module": "inventory"},
        {"name": "Ver Categoras", "codename": "categories:view", "module": "inventory"},
        
        # Proveedores y Compras
        {"name": "Ver Proveedores", "codename": "suppliers:view", "module": "inventory"},
        {"name": "Ver Compras", "codename": "purchases:view", "module": "inventory"},
        {"name": "Crear Compras", "codename": "purchases:create", "module": "inventory"},
        {"name": "Gestionar Compras", "codename": "purchases:manage", "module": "inventory"},

        # Lotes
        {"name": "Ver Lotes", "codename": "batches:view", "module": "inventory"},
        {"name": "Gestionar Lotes", "codename": "batches:manage", "module": "inventory"},
        
        # Inventario / Kardex / Ajustes
        {"name": "Ver Inventario", "codename": "inventory:view", "module": "inventory"},
        {"name": "Ver Ajustes", "codename": "adjustments:view", "module": "inventory"},
        {"name": "Realizar Ajustes", "codename": "adjustments:create", "module": "inventory"},
        {"name": "Ajustar Stock", "codename": "inventory:adjust", "module": "inventory"},
        
        # Gastos
        {"name": "Ver Gastos", "codename": "expenses:view", "module": "finance"},
        {"name": "Crear Gastos", "codename": "expenses:create", "module": "finance"},
        {"name": "Gestionar Gastos", "codename": "expenses:manage", "module": "finance"},
        {"name": "Exportar Gastos", "codename": "expenses:export", "module": "finance"},

        # Cotizaciones
        {"name": "Ver Cotizaciones", "codename": "quotes:view", "module": "sales"},
        {"name": "Crear Cotizaciones", "codename": "quotes:create", "module": "sales"},
        
        # Ventas
        {"name": "Ver Ventas", "codename": "sales:view", "module": "sales"},
        {"name": "Realizar Ventas", "codename": "sales:create", "module": "sales"},
        {"name": "Punto de Venta", "codename": "sales:pos", "module": "sales"},
        
        # Clientes
        {"name": "Ver Clientes", "codename": "customers:view", "module": "sales"},
        {"name": "Crear Clientes", "codename": "customers:create", "module": "sales"},

        # Sucursales
        {"name": "Ver Sucursales", "codename": "branches:view", "module": "admin"},
        {"name": "Crear Sucursales", "codename": "branches:create", "module": "admin"},
        {"name": "Editar Sucursales", "codename": "branches:edit", "module": "admin"},

        # Roles y Usuarios
        {"name": "Ver Usuarios", "codename": "users:view", "module": "admin"},
        {"name": "Ver Roles", "codename": "roles:view", "module": "admin"},
        {"name": "Gestionar Roles", "codename": "roles:manage", "module": "admin"},
        {"name": "Configuracion", "codename": "settings:manage", "module": "admin"},

        # Reportes
        {"name": "Ver Reportes", "codename": "reports:view", "module": "admin"},

        # Traslados
        {"name": "Ver Traslados", "codename": "transfers:view", "module": "inventory"},
        # Fidelizacin (Lealtad)
        {"name": "Ver Configuracin Lealtad", "codename": "loyalty:config_view", "module": "sales"},
        {"name": "Editar Configuracin Lealtad", "codename": "loyalty:config_edit", "module": "sales"},
        {"name": "Ver Historial Puntos", "codename": "loyalty:history_view", "module": "sales"},
        {"name": "Ajustar Puntos Manual", "codename": "loyalty:adjust", "module": "sales"},
        {"name": "Crear Traslados", "codename": "transfers:create", "module": "inventory"},
        {"name": "Gestionar Traslados", "codename": "transfers:manage", "module": "inventory"},

        # Cuentas por Cobrar (Crditos)
        {"name": "Ver Crditos", "codename": "credits:view", "module": "sales"},
        {"name": "Gestionar Crditos", "codename": "credits:manage", "module": "sales"},
        {"name": "Ver Pagos de Crdito", "codename": "payments:view", "module": "sales"},
        {"name": "Registrar Pagos de Crdito", "codename": "payments:create", "module": "sales"},
        
        # Barcodes & QR
        {"name": "Generar Barcodes", "codename": "barcodes:generate", "module": "inventory"},
        {"name": "Imprimir Etiquetas", "codename": "barcodes:print", "module": "inventory"},
        {"name": "Escanear Barcodes", "codename": "barcodes:scan", "module": "inventory"},

        # WMS Enhancements
        {"name": "Gestionar Auditorías", "codename": "inventory:audits", "module": "inventory"},
        {"name": "Ver Lista Picking", "codename": "sales:picking", "module": "sales"},
    ]
    
    # Crear todos los permisos
    from sqlalchemy import select
    all_perms = {}
    for p_data in permissions_data:
        res = await session.execute(select(Permission).where(Permission.codename == p_data["codename"]))
        perm = res.scalar_one_or_none()
        if not perm:
            perm = Permission(**p_data)
            session.add(perm)
            await session.flush()
            print(f"  OK Permiso: {perm.codename}")
        all_perms[p_data["codename"]] = perm
    
    # 2. Definir Roles y sus permisos
    roles_config = {
        "ADMIN": {
            "description": "Administrador total del Tenant",
            "is_system": True,
            "permissions": list(all_perms.keys()) # Todos los permisos
        },
        "MANAGER": {
            "description": "Gerente de Inventario y Ventas",
            "is_system": False,
            "permissions": [
                "dashboard:view",
                "products:view", "products:create", "products:edit",
                "categories:view", "suppliers:view",
                "purchases:view", "purchases:create", "purchases:manage",
                "batches:view", "batches:manage",
                "inventory:view", "inventory:adjust",
                "adjustments:view", "adjustments:create",
                "expenses:view", "expenses:create", "expenses:manage",
                "quotes:view", "quotes:create",
                "sales:view", "sales:pos", "sales:create",
                "customers:view", "customers:create",
                "transfers:view", "transfers:create", "transfers:manage",
                "branches:view", "users:view",
                "credits:view", "credits:manage", "payments:view", "payments:create",
                "loyalty:config_view", "loyalty:config_edit", "loyalty:history_view", "loyalty:adjust",
                "barcodes:generate", "barcodes:print", "barcodes:scan",
                "inventory:audits", "sales:picking"
            ]
        },
        "SELLER": {
            "description": "Vendedor / Punto de Venta",
            "is_system": True,
            "permissions": [
                "products:view", "batches:view", "inventory:view", "quotes:view", "quotes:create", "sales:pos",
                "loyalty:history_view"
            ]
        }
    }
    
    # Crear Roles y asignar permisos
    from sqlalchemy.orm import selectinload
    created_roles = {}
    for role_name, config in roles_config.items():
        res = await session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.name == role_name)
            .options(selectinload(Role.permissions))
        )
        role = res.scalar_one_or_none()
        if not role:
            role = Role(
                tenant_id=tenant_id,
                name=role_name,
                description=config["description"],
                is_system=config["is_system"]
            )
            session.add(role)
            await session.flush()
            print(f"  OK Rol creado: {role.name}")
        
        # Cargar permisos de forma explicita para evitar lazy loading
        await role.awaitable_attrs.permissions
        
        # Limpiar y re-asignar permisos para asegurar que estn sincronizados
        role.permissions = [all_perms[p_code] for p_code in config["permissions"]]
        created_roles[role_name] = role
        
    await session.commit()
    print("OK Roles y permisos sincronizados")
    return created_roles

async def create_products(
    session: AsyncSession,
    tenant_id: int,
    category_map: dict,
    supplier_map: dict
):
    """Crea los productos"""
    print("\n[INFO] Creando productos...")
    
    product_count = 0
    
    for prod_data in PRODUCTS:
        # Verificar si ya existe
        from sqlalchemy import select
        res = await session.execute(select(Product).where(Product.barcode == prod_data["barcode"]))
        product = res.scalar_one_or_none()
        if product:
            print(f"  - {prod_data['name']} (ya existe)")
            continue

        category = category_map.get(prod_data["category_code"])
        supplier = supplier_map.get(prod_data["supplier_code"])
        
        if not category or not supplier:
            print(f"    Saltando {prod_data['name']}: categora o proveedor no encontrado")
            continue
        
        product = Product(
            tenant_id=tenant_id,
            name=prod_data["name"],
            sku=prod_data["sku"],
            description=prod_data.get("description"),
            category_id=category.id,
            supplier_id=supplier.id,
            price=prod_data["price"],
            cost=prod_data.get("cost"),
            stock=prod_data.get("stock", 0),
            min_stock=prod_data.get("min_stock", 0),
            max_stock=prod_data.get("max_stock"),
            barcode=prod_data.get("barcode"),
            is_active=prod_data.get("is_active", True)
        )
        session.add(product)
        product_count += 1
        print(f"   {product.name} (Stock: {product.stock})")
    
    await session.commit()
    print(f" {product_count} productos creados")


async def run_seeds(clean: bool = False):
    """Ejecuta el proceso de seeds"""
    print("[INFO] Iniciando seeds de datos...\n")
    
    # Crear engine y session
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Limpiar si se solicita
            if clean:
                await clean_database(engine, session)
            
            # Crear datos
            tenant_id = await create_tenant_and_user(session)
            
            # Configuracion de Lealtad inicial
            from app.models.loyalty import LoyaltyConfig
            from sqlalchemy import select
            res = await session.execute(select(LoyaltyConfig).where(LoyaltyConfig.tenant_id == tenant_id))
            if not res.scalar_one_or_none():
                loyalty_config = LoyaltyConfig(
                    tenant_id=tenant_id,
                    points_per_amount=100.00, # 1 punto por cada $100
                    amount_per_point=10.00,   # 1 punto vale $10
                    is_active=True,
                    min_redemption_points=10
                )
                session.add(loyalty_config)
                await session.flush()
                print(" OK Configuracion de lealtad creada")
            
            roles = await create_roles_and_permissions(session, tenant_id)
            
            # Asignar rol ADMIN al usuario demo
            from sqlalchemy import select
            res = await session.execute(select(User).where(User.email == "admin@demo.com"))
            user = res.scalar_one()
            user.role_id = roles["ADMIN"].id
            user.role = UserRole.ADMIN
            await session.commit()
            
            category_map = await create_categories(session, tenant_id)
            supplier_map = await create_suppliers(session, tenant_id)
            await create_products(session, tenant_id, category_map, supplier_map)
            
            print("\n" + "="*60)
            print(" Seeds completados exitosamente!")
            print("="*60)
            print("\n Credenciales de acceso:")
            print("   Email: admin@demo.com")
            print("   Password: demo123")
            print("\n Accede a la aplicacin:")
            print("   http://localhost:8000/docs")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n Error durante seeds: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


def main():
    """Punto de entrada principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Poblar base de datos con datos de ejemplo")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Limpiar base de datos antes de crear datos"
    )
    
    args = parser.parse_args()
    
    # Ejecutar seeds
    asyncio.run(run_seeds(clean=args.clean))


if __name__ == "__main__":
    main()
