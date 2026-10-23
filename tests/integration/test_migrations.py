"""Las migraciones de Alembic: base nueva, datos reales divergentes, ida y vuelta y reglas de unicidad."""

import asyncio

import psycopg2
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from support import TEST_DATABASE_URL, alembic, sql

BASELINE = "6d4bc2ee2c32"
HEAD = "a1b2c3d4e5f6"


def count(table: str) -> int:
    return sql(f"SELECT count(*) FROM {table}", fetch=True)[0][0]


def test_fresh_database_builds_from_migrations_and_matches_the_models(blank_database):
    result = alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr[-1500:]
    tables = sql("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'", fetch=True)[0][0]
    assert tables >= 35
    assert sql("SELECT version_num FROM alembic_version", fetch=True)[0][0] == HEAD
    # si alguien cambia un modelo sin crear su migración, esto falla
    check = alembic("check")
    assert check.returncode == 0, f"Los modelos difieren de las migraciones:\n{check.stdout[-1500:]}{check.stderr[-1500:]}"


def test_upgrade_downgrade_roundtrip(blank_database):
    assert alembic("upgrade", "head").returncode == 0
    assert alembic("downgrade", BASELINE).returncode == 0
    assert alembic("upgrade", "head").returncode == 0
    assert alembic("check").returncode == 0


def test_stock_reconciliation_makes_product_stock_equal_to_the_sum_of_its_branches(blank_database):
    """Reproduce lo hallado en datos reales: ventas que solo tocaron products.stock."""
    assert alembic("upgrade", BASELINE).returncode == 0
    sql("INSERT INTO tenants (id, name, plan, created_at) VALUES (1, 'Acme', 'free', now()), (2, 'Sin sucursal', 'free', now())")
    sql("INSERT INTO branches (id, tenant_id, name, is_active, is_deleted, created_at, updated_at) VALUES "
        "(10, 1, 'Norte', true, false, now(), now()), (11, 1, 'Sucursal Principal', true, false, now(), now())")
    for pid, tenant, sku, stock in ((1, 1, 'SOBRA', 30), (2, 1, 'FALTA', 3), (3, 1, 'SIN-SUC', 7), (4, 1, 'OK', 5), (5, 2, 'T2', 4)):
        sql("INSERT INTO products (id, tenant_id, name, sku, price, stock, min_stock, is_active, is_deleted, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, 1, %s, 1, true, false, now(), now())", (pid, tenant, sku, sku, stock))
    # sucursales históricas: SOBRA suma 10 (products=30), FALTA suma 24 (products=3), OK coincide, SIN-SUC no tiene filas
    for pid, branch, stock in ((1, 10, 4), (1, 11, 6), (2, 10, 20), (2, 11, 4), (4, 11, 5)):
        sql("INSERT INTO product_branches (product_id, branch_id, stock, min_stock, created_at, updated_at) "
            "VALUES (%s, %s, %s, 1, now(), now())", (pid, branch, stock))
    sql("INSERT INTO users (id, email, hashed_password, is_active, is_admin, role, tenant_id, created_at, updated_at) "
        "VALUES (1, 'a@a.com', 'x', true, true, 'ADMIN', 1, now(), now())")
    sql("INSERT INTO sales (id, tenant_id, user_id, total_amount, payment_method, status, created_at, updated_at) "
        "VALUES (1, 1, 1, 10, 'cash', 'completed', now(), now())")

    result = alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr[-1500:]

    rows = sql("SELECT p.sku, p.stock, COALESCE(SUM(pb.stock), 0) FROM products p "
               "LEFT JOIN product_branches pb ON pb.product_id = p.id GROUP BY p.id ORDER BY p.id", fetch=True)
    assert all(stock == branches for _, stock, branches in rows), rows
    assert [stock for _, stock, _ in rows] == [30, 3, 7, 5, 4]  # products.stock se conserva
    assert sql("SELECT count(*) FROM product_branches WHERE stock < 0", fetch=True)[0][0] == 0
    # SOBRA: el excedente fue a la sucursal principal (11); FALTA: se descuenta empezando por la principal
    assert sql("SELECT stock FROM product_branches WHERE product_id=1 AND branch_id=11", fetch=True)[0][0] == 26
    assert sql("SELECT branch_id, stock FROM product_branches WHERE product_id=2 ORDER BY branch_id", fetch=True) == [(10, 3), (11, 0)]  # la principal se agota primero (4->0) y el resto sale de la otra (20->3)
    # el tenant sin sucursal recibió una y las ventas históricas tienen sucursal
    assert sql("SELECT count(*) FROM branches WHERE tenant_id=2", fetch=True)[0][0] == 1
    assert sql("SELECT branch_id FROM sales WHERE id=1", fetch=True)[0][0] == 11


def test_sku_and_barcode_are_unique_per_tenant_not_globally(blank_database):
    assert alembic("upgrade", "head").returncode == 0
    sql("INSERT INTO tenants (id, name, plan, created_at) VALUES (1, 'A', 'free', now()), (2, 'B', 'free', now())")

    def add(pid, tenant, sku, barcode=None, deleted=False):
        sql("INSERT INTO products (id, tenant_id, name, sku, barcode, price, stock, min_stock, is_active, is_deleted, created_at, updated_at) "
            "VALUES (%s, %s, 'n', %s, %s, 1, 0, 1, true, %s, now(), now())", (pid, tenant, sku, barcode, deleted))

    add(1, 1, "SKU-1", "BAR-1")
    add(2, 2, "SKU-1", "BAR-1")            # otro tenant: mismo SKU y código de barras permitidos
    with pytest.raises(psycopg2.errors.UniqueViolation):
        add(3, 1, "SKU-1")                 # mismo tenant: rechazado
    with pytest.raises(psycopg2.errors.UniqueViolation):
        add(4, 1, "SKU-X", "BAR-1")
    add(5, 1, "SKU-NULL-1")                # varios productos sin código de barras: permitido
    add(6, 1, "SKU-NULL-2")
    sql("UPDATE products SET is_deleted = true WHERE id = 1")
    add(7, 1, "SKU-1", "BAR-1")            # el SKU de un producto eliminado se puede reutilizar


def test_bootstrap_is_idempotent_and_fills_defaults(blank_database):
    from app.infrastructure.persistence.bootstrap import bootstrap_reference_data
    from app.infrastructure.persistence.permissions_catalog import PERMISSIONS

    assert alembic("upgrade", "head").returncode == 0
    sql("INSERT INTO tenants (name, plan, created_at) VALUES ('Acme', 'free', now())")

    async def boot_three_times():
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        for _ in range(3):  # reinicios de la app
            async with engine.begin() as conn:
                await bootstrap_reference_data(conn)
        await engine.dispose()

    asyncio.run(boot_three_times())
    assert count("permissions") == len(PERMISSIONS)
    assert count("branches") == 1 and sql("SELECT name FROM branches", fetch=True)[0][0] == "Sucursal Principal"
    assert count("expense_categories") == 5
    for codename in ("transfers:manage", "batches:view", "inventory:audits", "sales:picking", "credits:manage"):
        assert sql("SELECT count(*) FROM permissions WHERE codename=%s", (codename,), fetch=True)[0][0] == 1
