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
from app.seeds.data.categories import CATEGORIES
from app.seeds.data.suppliers import SUPPLIERS
from app.seeds.data.products import PRODUCTS


async def clean_database(engine, session: AsyncSession):
    """Limpia todos los datos de la base de datos recreando las tablas"""
    print("🗑️  Limpiando base de datos (recreando tablas)...")
    
    async with engine.begin() as conn:
        # Importante: Base.metadata necesita que todos los modelos estén cargados
        # lo cual ya ocurre arriba con los imports
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Base de datos recreada exitosamente")


async def create_tenant_and_user(session: AsyncSession):
    """Crea el tenant y usuario demo si no existen"""
    print("\n👤 Verificando tenant y usuario...")
    
    # Verificar si el usuario ya existe
    from sqlalchemy import select
    result = await session.execute(select(User).where(User.email == "admin@demo.com"))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        print(f"✅ Usuario demo ya existe: {existing_user.email}")
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
    
    print(f"✅ Tenant creado: {tenant.name} (ID: {tenant.id})")
    print(f"✅ Usuario creado: {user.email} / password: demo123")
    
    return tenant.id


async def create_categories(session: AsyncSession, tenant_id: int):
    """Crea las categorías jerárquicas"""
    print("\n📁 Creando categorías...")
    
    category_map = {}  # code -> Category object
    
    # Primera pasada: crear categorías raíz
    for cat_data in CATEGORIES:
        if cat_data["parent_code"] is None:
            # Verificar si ya existe
            from sqlalchemy import select
            res = await session.execute(select(Category).where(Category.code == cat_data["code"]))
            if res.scalar_one_or_none():
                category = res.scalar_one()
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
            print(f"  ✓ {category.name} ({category.code})")
    
    # Segunda pasada: crear categorías con padre
    for cat_data in CATEGORIES:
        if cat_data["parent_code"] is not None:
            # Verificar si ya existe
            from sqlalchemy import select
            res = await session.execute(select(Category).where(Category.code == cat_data["code"]))
            if res.scalar_one_or_none():
                category = res.scalar_one()
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
                print(f"    ✓ {category.name} ({category.code}) -> {parent.name}")
    
    await session.commit()
    print(f"✅ {len(category_map)} categorías creadas")
    
    return category_map


async def create_suppliers(session: AsyncSession, tenant_id: int):
    """Crea los proveedores"""
    print("\n🏢 Creando proveedores...")
    
    supplier_map = {}  # code -> Supplier object
    
    for sup_data in SUPPLIERS:
        # Verificar si ya existe
        from sqlalchemy import select
        res = await session.execute(select(Supplier).where(Supplier.code == sup_data["code"]))
        if res.scalar_one_or_none():
            supplier_map[sup_data["code"]] = res.scalar_one()
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
        print(f"  ✓ {supplier.name} ({supplier.code})")
    
    await session.commit()
    print(f"✅ {len(supplier_map)} proveedores creados")
    
    return supplier_map


async def create_products(
    session: AsyncSession,
    tenant_id: int,
    category_map: dict,
    supplier_map: dict
):
    """Crea los productos"""
    print("\n📦 Creando productos...")
    
    product_count = 0
    
    for prod_data in PRODUCTS:
        # Verificar si ya existe
        from sqlalchemy import select
        res = await session.execute(select(Product).where(Product.sku == prod_data["sku"]))
        if res.scalar_one_or_none():
            print(f"  - {prod_data['name']} (ya existe)")
            continue

        category = category_map.get(prod_data["category_code"])
        supplier = supplier_map.get(prod_data["supplier_code"])
        
        if not category or not supplier:
            print(f"  ⚠️  Saltando {prod_data['name']}: categoría o proveedor no encontrado")
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
        print(f"  ✓ {product.name} (Stock: {product.stock})")
    
    await session.commit()
    print(f"✅ {product_count} productos creados")


async def run_seeds(clean: bool = False):
    """Ejecuta el proceso de seeds"""
    print("🌱 Iniciando seeds de datos...\n")
    
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
            category_map = await create_categories(session, tenant_id)
            supplier_map = await create_suppliers(session, tenant_id)
            await create_products(session, tenant_id, category_map, supplier_map)
            
            print("\n" + "="*60)
            print("🎉 Seeds completados exitosamente!")
            print("="*60)
            print("\n📝 Credenciales de acceso:")
            print("   Email: admin@demo.com")
            print("   Password: demo123")
            print("\n🌐 Accede a la aplicación:")
            print("   http://localhost:8000/docs")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error durante seeds: {e}")
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
