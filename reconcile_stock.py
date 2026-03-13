import asyncio
from sqlalchemy import select
from app.models import Product
from app.models.product_branch import ProductBranch
from app.models.base import async_session, engine

async def reconcile():
    try:
        async with async_session() as db:
            print("Buscando productos con stock negativo...")
            
            # 1. Corregir en tabla products
            query_products = select(Product).where(Product.stock < 0)
            result_products = await db.execute(query_products)
            products = result_products.scalars().all()
            
            if products:
                print(f"Encontrados {len(products)} productos con stock negativo. Corrigiendo a 0...")
                for p in products:
                    print(f"Producto {p.sku}: {p.stock} -> 0")
                    p.stock = 0
            else:
                print("No se encontraron productos con stock negativo.")
                
            # 2. Corregir en tabla product_branches
            query_branches = select(ProductBranch).where(ProductBranch.stock < 0)
            result_branches = await db.execute(query_branches)
            branches = result_branches.scalars().all()
            
            if branches:
                print(f"Encontradas {len(branches)} sucursales con stock negativo. Corrigiendo a 0...")
                for b in branches:
                    print(f"Sucursal {b.branch_id}, Producto {b.product_id}: {b.stock} -> 0")
                    b.stock = 0
            else:
                print("No se encontraron sucursales con stock negativo.")
                
            await db.commit()
            print("Sincronización completada.")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reconcile())
