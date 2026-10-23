"""stock por sucursal y unicidad por tenant

Revision ID: a1b2c3d4e5f6
Revises: 6d4bc2ee2c32
Create Date: 2026-10-22 17:08:27.250095

1. SKU y código de barras pasan de únicos GLOBALES a únicos POR TENANT (solo entre productos
   no eliminados), de modo que dos negocios puedan usar el mismo SKU y se pueda recrear el
   SKU de un producto borrado lógicamente.
2. `sales.branch_id`: sucursal que despachó la venta (necesaria para devolver el stock al anular).
3. Stock por sucursal como fuente de verdad: `products.stock` debe ser SIEMPRE la suma de
   `product_branches.stock`. Hasta ahora ventas y ajustes solo tocaban `products.stock`, por lo
   que ambos modelos podían divergir. Esta migración los concilia conservando `products.stock`
   (lo que el sistema mostraba) y llevando la diferencia a la sucursal principal de cada tenant.
   Si tras conciliar queda cualquier producto inconsistente, la migración ABORTA (y se revierte).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6d4bc2ee2c32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MAIN_BRANCH_NAME = "Sucursal Principal"


def _ensure_main_branches(conn) -> dict[int, int]:
    """Garantiza una sucursal por tenant y devuelve {tenant_id: id de su sucursal principal}."""
    conn.execute(sa.text("""
        INSERT INTO branches (tenant_id, name, is_active, is_deleted, created_at, updated_at)
        SELECT t.id, :name, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM tenants t
        WHERE NOT EXISTS (SELECT 1 FROM branches b WHERE b.tenant_id = t.id AND b.is_deleted = false)
    """), {"name": MAIN_BRANCH_NAME})
    rows = conn.execute(sa.text("""
        SELECT DISTINCT ON (tenant_id) tenant_id, id
        FROM branches
        WHERE is_deleted = false
        ORDER BY tenant_id, (name = :name) DESC, id ASC
    """), {"name": MAIN_BRANCH_NAME}).all()
    return {tenant_id: branch_id for tenant_id, branch_id in rows}


def _reconcile_stock(conn, main_branch: dict[int, int]) -> None:
    products = conn.execute(sa.text("""
        SELECT p.id, p.tenant_id, p.stock, p.min_stock, p.max_stock,
               COALESCE((SELECT SUM(pb.stock) FROM product_branches pb WHERE pb.product_id = p.id), 0) AS branch_total
        FROM products p
    """)).all()
    for product_id, tenant_id, stock, min_stock, max_stock, branch_total in products:
        delta = int(stock) - int(branch_total)
        if delta == 0:
            continue
        main_id = main_branch[tenant_id]
        positions = conn.execute(sa.text("""
            SELECT id, branch_id, stock FROM product_branches
            WHERE product_id = :p ORDER BY (branch_id = :main) DESC, branch_id ASC
        """), {"p": product_id, "main": main_id}).all()

        if not positions:
            conn.execute(sa.text("""
                INSERT INTO product_branches (product_id, branch_id, stock, min_stock, max_stock, created_at, updated_at)
                VALUES (:p, :b, :s, :mn, :mx, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """), {"p": product_id, "b": main_id, "s": delta, "mn": min_stock, "mx": max_stock})
            continue

        if delta > 0:  # sobra en el producto: se suma a la sucursal principal
            target = next((pos for pos in positions if pos.branch_id == main_id), None)
            if target is None:
                conn.execute(sa.text("""
                    INSERT INTO product_branches (product_id, branch_id, stock, min_stock, max_stock, created_at, updated_at)
                    VALUES (:p, :b, :s, :mn, :mx, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """), {"p": product_id, "b": main_id, "s": delta, "mn": min_stock, "mx": max_stock})
            else:
                conn.execute(sa.text("UPDATE product_branches SET stock = stock + :d WHERE id = :id"),
                             {"d": delta, "id": target.id})
            continue

        # faltan unidades en el producto (ventas antiguas que no tocaron sucursales): se descuentan,
        # primero de la principal y luego de las demás, sin dejar negativos mientras haya stock
        remaining = -delta
        for position in positions:
            take = min(remaining, max(int(position.stock), 0))
            if take:
                conn.execute(sa.text("UPDATE product_branches SET stock = stock - :t WHERE id = :id"),
                             {"t": take, "id": position.id})
                remaining -= take
            if remaining == 0:
                break
        if remaining:  # el producto ya estaba en negativo respecto a todas sus sucursales
            conn.execute(sa.text("UPDATE product_branches SET stock = stock - :t WHERE id = :id"),
                         {"t": remaining, "id": positions[0].id})


def _assert_consistent(conn) -> None:
    broken = conn.execute(sa.text("""
        SELECT COUNT(*) FROM products p
        WHERE p.stock <> COALESCE((SELECT SUM(pb.stock) FROM product_branches pb WHERE pb.product_id = p.id), 0)
    """)).scalar()
    if broken:
        raise RuntimeError(f"Conciliación de stock incompleta: {broken} productos siguen inconsistentes")


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1. unicidad por tenant (parcial: ignora productos eliminados) ---
    op.execute("DROP INDEX IF EXISTS ix_products_barcode")
    op.create_index(op.f('ix_products_barcode'), 'products', ['barcode'], unique=False)
    op.execute("DROP INDEX IF EXISTS ix_products_sku")
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=False)
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_sku_key")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_barcode_key")
    op.create_index('uq_products_tenant_barcode', 'products', ['tenant_id', 'barcode'], unique=True,
                    postgresql_where=sa.text('is_deleted = false AND barcode IS NOT NULL'))
    op.create_index('uq_products_tenant_sku', 'products', ['tenant_id', 'sku'], unique=True,
                    postgresql_where=sa.text('is_deleted = false'))

    # --- 2. sucursal de la venta ---
    op.add_column('sales', sa.Column('branch_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_sales_branch_id'), 'sales', ['branch_id'], unique=False)
    op.create_foreign_key('fk_sales_branch_id', 'sales', 'branches', ['branch_id'], ['id'])

    # --- 3. datos: sucursal principal, ventas históricas y conciliación de stock ---
    main_branch = _ensure_main_branches(conn)
    for tenant_id, branch_id in main_branch.items():
        conn.execute(sa.text("UPDATE sales SET branch_id = :b WHERE tenant_id = :t AND branch_id IS NULL"),
                     {"b": branch_id, "t": tenant_id})
    _reconcile_stock(conn, main_branch)
    _assert_consistent(conn)


def downgrade() -> None:
    # Los datos conciliados NO se revierten. Recrear los únicos globales falla si hay SKU repetidos entre tenants.
    op.drop_constraint('fk_sales_branch_id', 'sales', type_='foreignkey')
    op.drop_index(op.f('ix_sales_branch_id'), table_name='sales')
    op.drop_column('sales', 'branch_id')
    op.drop_index('uq_products_tenant_sku', table_name='products', postgresql_where=sa.text('is_deleted = false'))
    op.drop_index('uq_products_tenant_barcode', table_name='products',
                  postgresql_where=sa.text('is_deleted = false AND barcode IS NOT NULL'))
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.create_index('ix_products_sku', 'products', ['sku'], unique=True)
    op.drop_index(op.f('ix_products_barcode'), table_name='products')
    op.create_index('ix_products_barcode', 'products', ['barcode'], unique=True)
